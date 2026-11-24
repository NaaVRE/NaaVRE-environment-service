import json

import httpx
import pytest
import respx

from app.jobs import rebuild_environments as job
from app.tests.routes.helpers import CATALOGUE_URL, catalogue_list_response

SERVICE_URL = "http://environment-service.test:8000"
TOKEN = "rebuilder-token"
BUILD_ATTEMPTS = 2


@pytest.fixture(autouse=True)
def rebuilder_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMAGE_REBUILDER_SERVICE_URL", SERVICE_URL + "/")
    monkeypatch.setenv("IMAGE_REBUILDER_TOKEN", TOKEN)
    monkeypatch.setenv("IMAGE_REBUILDER_WAIT_TIMEOUT", "1")
    monkeypatch.setenv("IMAGE_REBUILDER_WAIT_RETRY_INTERVAL", "0")
    monkeypatch.setenv("IMAGE_REBUILDER_BUILD_ATTEMPTS", str(BUILD_ATTEMPTS))


def catalogue_environment(binder_ref: str) -> dict:
    return {
        "url": f"{CATALOGUE_URL}/binder-environments/{binder_ref}/",
        "binder_ref": binder_ref,
        "container_image": f"registry.test/{binder_ref}:old",
        "pre_pull": True,
        "has_container_image": True,
        }


def mock_catalogue(binder_refs: list[str]) -> respx.Route:
    return respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"pre_pull": "true", "has_container_image": "true"},
        ).respond(
        200,
        json=catalogue_list_response(
            results=[catalogue_environment(ref) for ref in binder_refs]
            ),
        )


def mock_me() -> respx.Route:
    return respx.get(f"{SERVICE_URL}/me").respond(
        200, json={"user": {"id": "__helm_image_rebuilder"}}
        )


def sse(*events: dict) -> str:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events)


def built_stream(image: str) -> httpx.Response:
    return httpx.Response(200, text=sse(
        {"phase": "waiting", "message": "Waiting\n"},
        {"phase": "building", "message": "Step 1/2\n"},
        {"phase": "built", "message": "Built image", "imageName": image},
        ))


@respx.mock
def test_rebuilds_all_pre_pull_environments() -> None:
    catalogue = mock_catalogue(["gh/acme/one/main", "gh/acme/two/v1.0"])
    mock_me()
    build_one = respx.post(f"{SERVICE_URL}/build/gh/acme/one/main").mock(
        return_value=built_stream("registry.test/one:new")
        )
    build_two = respx.post(f"{SERVICE_URL}/build/gh/acme/two/v1.0").mock(
        return_value=built_stream("registry.test/two:new")
        )

    assert job.main() == 0

    assert catalogue.called
    assert build_one.call_count == 1
    assert build_two.call_count == 1
    assert (build_one.calls.last.request.headers["Authorization"]
            == f"Bearer {TOKEN}")


@respx.mock
def test_no_environments_does_not_call_service() -> None:
    mock_catalogue([])
    mock_me()

    assert job.main() == 0


@respx.mock
def test_failed_build_is_reported_and_not_retried() -> None:
    mock_catalogue(["gh/acme/one/main", "gh/acme/two/main"])
    mock_me()
    build_one = respx.post(f"{SERVICE_URL}/build/gh/acme/one/main").respond(
        200, text=sse({"phase": "failed", "message": "failed"})
        )
    build_two = respx.post(f"{SERVICE_URL}/build/gh/acme/two/main").mock(
        return_value=built_stream("registry.test/two:new")
        )

    assert job.main() == 1
    assert build_one.call_count == 1
    # Other environments are still built after a failure
    assert build_two.call_count == 1


@respx.mock
def test_interrupted_build_is_retried() -> None:
    mock_catalogue(["gh/acme/one/main"])
    mock_me()
    build = respx.post(f"{SERVICE_URL}/build/gh/acme/one/main").mock(
        side_effect=[
            httpx.Response(200, text=sse({"phase": "building"})),
            built_stream("registry.test/one:new"),
            ]
        )

    assert job.main() == 0
    assert build.call_count == 2


@respx.mock
def test_build_fails_after_max_attempts() -> None:
    mock_catalogue(["gh/acme/one/main"])
    mock_me()
    build = respx.post(f"{SERVICE_URL}/build/gh/acme/one/main").mock(
        side_effect=httpx.ConnectError("connection refused")
        )

    assert job.main() == 1
    assert build.call_count == BUILD_ATTEMPTS


@respx.mock
def test_waits_for_catalogue_and_service() -> None:
    catalogue = respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"pre_pull": "true", "has_container_image": "true"},
        ).mock(side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=catalogue_list_response(
                results=[catalogue_environment("gh/acme/one/main")]
                )),
            ])
    me = respx.get(f"{SERVICE_URL}/me").mock(side_effect=[
        httpx.ConnectError("connection refused"),
        httpx.Response(403),
        httpx.Response(200, json={}),
        ])
    respx.post(f"{SERVICE_URL}/build/gh/acme/one/main").mock(
        return_value=built_stream("registry.test/one:new")
        )

    assert job.main() == 0
    assert catalogue.call_count == 2
    assert me.call_count == 3


@respx.mock
def test_unsupported_binder_ref_fails() -> None:
    mock_catalogue(["gl/acme/one/main"])
    mock_me()

    assert job.main() == 1


@pytest.mark.parametrize(("binder_ref", "expected"), [
    ("gh/acme/demo/main", "/build/gh/acme/demo/main"),
    ("gh/acme/demo/a b", "/build/gh/acme/demo/a%20b"),
    ("gh/acme/demo/feature/x", None),
    ("gh/acme/demo", None),
    ("gh/acme", None),
    ("gh/", None),
    ("gl/acme/demo/main", None),
    ])
def test_build_route_path(binder_ref: str, expected: str | None) -> None:
    assert job.build_route_path(binder_ref) == expected
