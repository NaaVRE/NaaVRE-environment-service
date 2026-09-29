from unittest.mock import Mock

from fastapi.testclient import TestClient
from kubernetes import client
import pytest
import respx
import urllib3

from app.main import app
from app.services import k8s
from app.tests.routes.helpers import CATALOGUE_URL, catalogue_list_response

TOKEN = "test-token"
KUBE_NAMESPACE = "test-namespace"
IMAGE_PULLER_NAME = "test-image-puller"
PAUSE_IMAGE = "registry.test/pause:latest"


@pytest.fixture
def mock_kube_api(monkeypatch: pytest.MonkeyPatch) -> Mock:
    monkeypatch.setenv("IMAGE_PULLER_NAMESPACE", KUBE_NAMESPACE)
    monkeypatch.setenv("IMAGE_PULLER_NAME", IMAGE_PULLER_NAME)
    monkeypatch.setenv("IMAGE_PULLER_PAUSE_IMAGE", PAUSE_IMAGE)

    apps_api = Mock()
    monkeypatch.setattr(k8s.config, "load_incluster_config", Mock())
    monkeypatch.setattr(
        k8s.client, "AppsV1Api", Mock(return_value=apps_api)
        )
    return apps_api


def mock_pre_pull_catalogue(environments: list[dict]) -> respx.Route:
    return respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"pre_pull": "true"},
        ).respond(
        200, json=catalogue_list_response(results=environments)
        )


def catalogue_environment(binder_ref: str, image: str) -> dict:
    return {
        "url": f"{CATALOGUE_URL}/binder-environments/{binder_ref}/",
        "binder_ref": binder_ref,
        "container_image": image,
        "pre_pull": True,
        }


@respx.mock
def test_sync_creates_daemonset_with_one_image(
        mock_kube_api: Mock,
        ) -> None:
    image = "registry.test/acme/demo:one"
    catalogue_get = mock_pre_pull_catalogue(
        [catalogue_environment("gh/acme/demo/main", image)]
        )
    mock_kube_api.read_namespaced_daemon_set.side_effect = (
        client.ApiException(status=404, reason="Not Found")
        )

    with TestClient(app) as test_client:
        response = test_client.post(
            "/image-puller/sync",
            headers={"Authorization": f"Bearer {TOKEN}"},
            )

    assert response.status_code == 200
    assert response.json() == {"outcome": "created", "image_count": 1}
    assert catalogue_get.called
    mock_kube_api.read_namespaced_daemon_set.assert_called_once_with(
        name=IMAGE_PULLER_NAME,
        namespace=KUBE_NAMESPACE,
        )
    mock_kube_api.create_namespaced_daemon_set.assert_called_once()
    mock_kube_api.replace_namespaced_daemon_set.assert_not_called()
    daemonset = mock_kube_api.create_namespaced_daemon_set.call_args.kwargs[
        "body"
        ]
    assert daemonset.spec.template.spec.init_containers[0].image == image
    assert daemonset.spec.template.spec.containers[0].image == PAUSE_IMAGE


@respx.mock
def test_sync_updates_daemonset_with_two_images(
        mock_kube_api: Mock,
        ) -> None:
    images = [
        "registry.test/acme/demo:one",
        "registry.test/acme/demo:two",
        ]
    catalogue_get = mock_pre_pull_catalogue([
        catalogue_environment("gh/acme/demo/one", images[0]),
        catalogue_environment("gh/acme/demo/two", images[1]),
        ])
    mock_kube_api.read_namespaced_daemon_set.return_value = (
        client.V1DaemonSet(
            metadata=client.V1ObjectMeta(resource_version="1")
            )
        )

    with TestClient(app) as test_client:
        response = test_client.post(
            "/image-puller/sync",
            headers={"Authorization": f"Bearer {TOKEN}"},
            )

    assert response.status_code == 200
    assert response.json() == {"outcome": "updated", "image_count": 2}
    assert catalogue_get.called
    mock_kube_api.replace_namespaced_daemon_set.assert_called_once()
    mock_kube_api.create_namespaced_daemon_set.assert_not_called()
    daemonset = mock_kube_api.replace_namespaced_daemon_set.call_args.kwargs[
        "body"
        ]
    assert [container.image for container
            in daemonset.spec.template.spec.init_containers] == images
    assert daemonset.metadata.resource_version == "1"


@respx.mock
def test_sync_fails_when_unable_to_connect_to_kube_api(
        mock_kube_api: Mock,
        ) -> None:
    catalogue_get = mock_pre_pull_catalogue([])
    mock_kube_api.read_namespaced_daemon_set.side_effect = (
        urllib3.exceptions.MaxRetryError(
            None, "kube-api", reason=ConnectionError("connection refused")
            )
        )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/image-puller/sync",
            headers={"Authorization": f"Bearer {TOKEN}"},
            )

    assert response.status_code == 500
    assert catalogue_get.called
    mock_kube_api.read_namespaced_daemon_set.assert_called_once()
    mock_kube_api.create_namespaced_daemon_set.assert_not_called()
    mock_kube_api.replace_namespaced_daemon_set.assert_not_called()


@respx.mock
def test_sync_fails_when_kube_api_authentication_fails(
        mock_kube_api: Mock,
        ) -> None:
    catalogue_get = mock_pre_pull_catalogue([])
    mock_kube_api.read_namespaced_daemon_set.side_effect = (
        client.ApiException(status=401, reason="Unauthorized")
        )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/image-puller/sync",
            headers={"Authorization": f"Bearer {TOKEN}"},
            )

    assert response.status_code == 500
    assert catalogue_get.called
    mock_kube_api.read_namespaced_daemon_set.assert_called_once()
    mock_kube_api.create_namespaced_daemon_set.assert_not_called()
    mock_kube_api.replace_namespaced_daemon_set.assert_not_called()
