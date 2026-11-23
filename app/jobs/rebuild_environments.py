""" Get Binder environments from the catalogue and rebuild them

Invocation:

    python -m app.jobs.rebuild_environments

Steps:
1. List the environments catalogue for which pre_pull and
   has_container_image are true.
2. For each environment, call the build route of the environment
   service and wait for the build result.

The process exits with a non-zero status if any build fails.
"""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
import sys
import time
from urllib.parse import quote

import httpx
import pydantic

from app import env
from app.services.binder import BinderBuildEvent
from app.services.catalogue import (
    BinderEnvironmentResponse,
    get_pre_pull_environments,
    )

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    binder_ref: str
    success: bool
    image_name: str | None = None
    message: str | None = None


class IncompleteBuildStream(Exception):
    """ The build stream ended before reaching a terminal phase """


async def _retry[T](
        func: Callable[[], Awaitable[T]],
        description: str,
        ) -> T:
    """ Call `func` until it succeeds or `timeout` seconds have elapsed """
    timeout = env.IMAGE_REBUILDER_WAIT_TIMEOUT
    interval = env.IMAGE_REBUILDER_WAIT_RETRY_INTERVAL
    deadline = time.monotonic() + timeout
    while True:
        try:
            return await func()
        except Exception as exc:
            if time.monotonic() + interval > deadline:
                logger.error(f"Giving up on {description}: {exc}")
                raise
            logger.warning(
                f"{description} failed ({exc}), retrying in {interval}s"
                )
            await asyncio.sleep(interval)


async def list_environments() -> list[BinderEnvironmentResponse]:
    """ list environments to be rebuilt """
    return [
        environment for environment in await _retry(
            get_pre_pull_environments,
            "listing environments from the catalogue",
            )
        if environment.container_image
        ]


async def wait_for_environment_service(client: httpx.AsyncClient) -> None:
    """ Wait for the environment service """

    async def check() -> None:
        resp = await client.get(f"{env.IMAGE_REBUILDER_SERVICE_URL}/me")
        resp.raise_for_status()

    await _retry(
        check,
        "waiting for the environment service",
        )


def build_route_path(binder_ref: str) -> str | None:
    """ Convert a binder_ref (`gh/{org}/{repo}/{ref}`) to a build route path

    Returns None if the binder_ref is not supported by the build route.
    """
    parts = binder_ref.split("/")
    if len(parts) != 4 or parts[0] != "gh" or not all(parts):
        return None
    _, org, repo, ref = parts
    return "/build/gh/" + "/".join(quote(p, safe="") for p in (org, repo, ref))


async def _build_once(
        client: httpx.AsyncClient,
        binder_ref: str,
        path: str,
        ) -> BuildResult:
    """ Call the build route and consume its SSE stream until it ends

    Raises IncompleteBuildStream if the stream ends without a terminal phase
    (e.g. because the service pod was restarted).
    """
    last_event: BinderBuildEvent | None = None
    async with client.stream(
            "POST", f"{env.IMAGE_REBUILDER_SERVICE_URL}{path}"
            ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            try:
                event = BinderBuildEvent.model_validate_json(
                    line[len("data:"):].strip()
                    )
            except pydantic.ValidationError:
                continue
            if event.message:
                logger.debug(f"[{binder_ref}] {event.message.rstrip()}")
            if event.phase:
                last_event = event

    if last_event is None or last_event.phase not in {"built", "failed"}:
        raise IncompleteBuildStream(
            f"build stream ended in phase "
            f"{last_event.phase if last_event else None!r}"
            )
    return BuildResult(
        binder_ref=binder_ref,
        success=last_event.phase == "built",
        image_name=last_event.imageName,
        message=last_event.message,
        )


async def rebuild_environment(
        client: httpx.AsyncClient,
        environment: BinderEnvironmentResponse,
        ) -> BuildResult:
    """ call the build route for one environment and wait for the result

    Builds are retried on connection errors and interrupted streams, but not
    when the build itself reports a failure.
    """
    binder_ref = environment.binder_ref
    path = build_route_path(binder_ref)
    if path is None:
        return BuildResult(
            binder_ref=binder_ref,
            success=False,
            message=f"Unsupported binder_ref: {binder_ref}",
            )

    attempts = env.IMAGE_REBUILDER_BUILD_ATTEMPTS
    last_error = None
    for attempt in range(1, attempts + 1):
        logger.info(f"Building {binder_ref} (attempt {attempt}/{attempts})")
        try:
            return await _build_once(client, binder_ref, path)
        except (httpx.HTTPError, IncompleteBuildStream) as exc:
            logger.warning(f"Build of {binder_ref} interrupted: {exc}")
            last_error = exc
    return BuildResult(
        binder_ref=binder_ref,
        success=False,
        message=f"Build interrupted after {attempts} attempt(s): "
                f"{last_error}",
        )


async def rebuild_environments() -> list[BuildResult]:
    async with httpx.AsyncClient(
            timeout=httpx.Timeout(30, read=None),
            verify=env.VERIFY_SSL,
            headers={
                "Authorization": f"Bearer {env.IMAGE_REBUILDER_TOKEN}",
                },
            ) as environment_service_client:
        environments = await list_environments()
        logger.info(
            f"Found {len(environments)} environment(s) to rebuild"
            )
        if not environments:
            return []

        await wait_for_environment_service(environment_service_client)

        results = []
        for environment in environments:
            result = await rebuild_environment(
                environment_service_client, environment
                )
            if result.success:
                logger.info(
                    f"Built {result.binder_ref}: {result.image_name}"
                    )
            else:
                logger.error(
                    f"Failed to build {result.binder_ref}: {result.message}"
                    )
            results.append(result)
        return results


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG if env.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    results = asyncio.run(rebuild_environments())
    failed = [r for r in results if not r.success]
    logger.info(
        f"Rebuilt {len(results) - len(failed)}/{len(results)} "
        "environment(s)"
        )
    for result in failed:
        logger.error(f"  failed: {result.binder_ref}: {result.message}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
