from collections.abc import AsyncIterator
import json
import logging

from fastapi.testclient import TestClient
import httpx
import respx

from app.main import app

logger = logging.getLogger(__name__)

BINDER_URL = "https://binder.test"
CATALOGUE_URL = "https://catalogue.test"
BINDER_API_TOKEN = "binder-test-token"
CATALOGUE_API_TOKEN = "catalogue-test-token"


class MockStreamingResponse(httpx.AsyncByteStream):
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for line in self.lines:
            yield line.encode("utf-8")


def mock_stream(*events: dict[str, str]) -> MockStreamingResponse:
    return MockStreamingResponse(
        [f"data: {json.dumps(event)}\n\n" for event in events]
        )


def catalogue_list_response(*, results: list[dict]) -> dict:
    return {
        "count": len(results),
        "next": None,
        "previous": None,
        "results": results,
        }


@respx.mock
def test_build_creates_catalogue_record():
    binder_ref = "gh/acme/demo/main"
    image_name = "registry.test/acme/demo:abc123"

    binder_get = respx.get(
        f"{BINDER_URL}/build/{binder_ref}",
        headers={
            "accept": "text/event-stream",
            "authorization": f"Bearer {BINDER_API_TOKEN}",
            },
        ).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=mock_stream(
                {"phase": "building", "message": "Starting mock build"},
                {
                    "phase": "built",
                    "message": "Mock build complete",
                    "imageName": image_name,
                    },
                ),
            )
        )

    catalogue_get = respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"binder_ref": binder_ref},
        ).respond(200, json=catalogue_list_response(results=[]))
    catalogue_post = respx.post(
        f"{CATALOGUE_URL}/binder-environments/",
        headers={"authorization": f"Token {CATALOGUE_API_TOKEN}"},
        ).respond(
        201, json={"url": f"{CATALOGUE_URL}/binder-environments/1/"}
        )

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert response.text == ''.join(
        (
            'data: {"phase": "building", "message": "Starting mock build"}\n\n'
            'data: {"phase": "built", "message": "Mock build complete", '
            f'"imageName": "{image_name}"}}\n'
        )
        )

    assert binder_get.called
    assert catalogue_get.called
    assert catalogue_post.called
    assert json.loads(catalogue_post.calls.last.request.content) == {
        "binder_ref": binder_ref,
        "container_image": image_name,
        }


@respx.mock
def test_build_updates_existing_catalogue_record():
    binder_ref = "gh/acme/demo/main"
    image_name = "registry.test/acme/demo:abc123"
    record_url = (f"{CATALOGUE_URL}/binder-environments/"
                  f"cb6d1a6e-cea6-47c3-831c-d8e8efd81c7a/")

    respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(
        return_value=httpx.Response(
            200,
            stream=mock_stream(
                {
                    "phase": "built",
                    "message": "Mock build complete",
                    "imageName": image_name,
                    },
                ),
            )
        )
    respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"binder_ref": binder_ref},
        ).respond(
        200,
        json=catalogue_list_response(
            results=[
                {
                    "url": record_url,
                    "binder_ref": binder_ref,
                    "container_image": "",
                    "pre_pull": False,
                    }
                ]
            ),
        )
    catalogue_put = respx.put(
        record_url,
        headers={"authorization": f"Token {CATALOGUE_API_TOKEN}"},
        ).respond(200, json={})

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert response.status_code == 200
    assert '"phase": "built"' in response.text
    assert catalogue_put.called
    assert json.loads(catalogue_put.calls.last.request.content) == {
        "binder_ref": binder_ref,
        "container_image": image_name,
        }


@respx.mock
def test_failed_build_does_not_upsert_catalogue() -> None:
    binder_ref = "gh/acme/demo/broken"

    binder_get = respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(
        return_value=httpx.Response(
            200,
            stream=mock_stream(
                {"phase": "building", "message": "Starting mock build"},
                {"phase": "failed", "message": "Mock build failed"},
                ),
            )
        )
    catalogue_get = respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"binder_ref": binder_ref},
        ).respond(200, json=catalogue_list_response(results=[]))

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert binder_get.called
    assert catalogue_get.called == False
    assert response.status_code == 200
    assert response.text == ''.join((
        'data: {"phase": "building", "message": "Starting mock build"}\n\n'
        'data: {"phase": "failed", "message": "Mock build failed"}\n'
    ))


@respx.mock
def test_binder_unknown_event() -> None:
    binder_ref = "gh/acme/demo/unknown_event"
    binder_get = respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(
        return_value=httpx.Response(
            200,
            stream=mock_stream(
                 {"phase": "unknown", "message": False},
                ),
            )
        )

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert binder_get.called
    assert response.status_code == 200
    assert '"phase": "unknown", "message": false' in response.text


@respx.mock
def test_binder_http_status_error() -> None:
    binder_ref = "gh/acme/demo/missing"
    binder_get = respx.get(f"{BINDER_URL}/build/{binder_ref}").respond(
        404, json={"detail": "Not found"}
        )

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert binder_get.called
    assert response.status_code == 200
    assert '"phase": "failed"' in response.text
    assert f"Binder build request failed ({binder_ref})" in response.text


@respx.mock
def test_binder_connect_error() -> None:
    binder_ref = "gh/acme/demo/connect_error"
    binder_get = respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(side_effect=httpx.ConnectError)

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert binder_get.called
    assert response.status_code == 200
    assert '"phase": "failed"' in response.text
    assert f"Unexpected error watching Binder build for {binder_ref}" in response.text


@respx.mock
def test_catalogue_get_error():
    binder_ref = "gh/acme/demo/main"
    image_name = "registry.test/acme/demo:abc123"

    respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(
        return_value=httpx.Response(
            200,
            stream=mock_stream(
                {
                    "phase": "built",
                    "message": "Mock build complete",
                    "imageName": image_name,
                    },
                ),
            )
        )
    catalogue_get = respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"binder_ref": binder_ref},
        ).mock(side_effect=httpx.ConnectError)

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert response.status_code == 200
    assert '"phase": "built"' in response.text
    assert catalogue_get.called


@respx.mock
def test_catalogue_get_inconsistent():
    binder_ref = "gh/acme/demo/main"
    image_name = "registry.test/acme/demo:abc123"

    respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(
        return_value=httpx.Response(
            200,
            stream=mock_stream(
                {
                    "phase": "built",
                    "message": "Mock build complete",
                    "imageName": image_name,
                    },
                ),
            )
        )
    catalogue_get = respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"binder_ref": binder_ref},
        ).respond(
        200,
        json=catalogue_list_response(
            results=[
                {
                    "url": f"${CATALOGUE_URL}/binder-environments/1",
                    "binder_ref": binder_ref,
                    "container_image": "",
                    "pre_pull": False,
                    },
                {
                    "url": f"${CATALOGUE_URL}/binder-environments/2",
                    "binder_ref": binder_ref,
                    "container_image": "",
                    "pre_pull": False,
                    }
                ]
            ),
        )

    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert response.status_code == 200
    assert '"phase": "built"' in response.text
    assert catalogue_get.called

@respx.mock
def test_catalogue_post_error():
    binder_ref = "gh/acme/demo/main"
    image_name = "registry.test/acme/demo:abc123"

    respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(
        return_value=httpx.Response(
            200,
            stream=mock_stream(
                {
                    "phase": "built",
                    "message": "Mock build complete",
                    "imageName": image_name,
                    },
                ),
            )
        )
    catalogue_get = respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"binder_ref": binder_ref},
        ).respond(200, json=catalogue_list_response(results=[]))
    catalogue_post = respx.post(
        f"{CATALOGUE_URL}/binder-environments/",
        headers={"authorization": f"Token {CATALOGUE_API_TOKEN}"},
        ).mock(side_effect=httpx.ConnectError)


    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert response.status_code == 200
    assert '"phase": "built"' in response.text
    assert catalogue_get.called


@respx.mock
def test_catalogue_put_error():
    binder_ref = "gh/acme/demo/main"
    image_name = "registry.test/acme/demo:abc123"
    record_url = (f"{CATALOGUE_URL}/binder-environments/"
                  f"cb6d1a6e-cea6-47c3-831c-d8e8efd81c7a/")

    respx.get(f"{BINDER_URL}/build/{binder_ref}").mock(
        return_value=httpx.Response(
            200,
            stream=mock_stream(
                {
                    "phase": "built",
                    "message": "Mock build complete",
                    "imageName": image_name,
                    },
                ),
            )
        )
    respx.get(
        f"{CATALOGUE_URL}/binder-environments/",
        params={"binder_ref": binder_ref},
        ).respond(
        200,
        json=catalogue_list_response(
            results=[
                {
                    "url": record_url,
                    "binder_ref": binder_ref,
                    "container_image": "",
                    "pre_pull": False,
                    }
                ]
            ),
        )
    catalogue_put = respx.put(
        record_url,
        headers={"authorization": f"Token {CATALOGUE_API_TOKEN}"},
        ).mock(side_effect=httpx.ConnectError)


    with TestClient(app) as client:
        response = client.post(f"/build/{binder_ref}")

    assert response.status_code == 200
    assert '"phase": "built"' in response.text
    assert catalogue_put.called
