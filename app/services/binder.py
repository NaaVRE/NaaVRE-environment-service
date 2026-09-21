from collections.abc import AsyncGenerator
import json
import logging
from typing import Tuple

import httpx
import pydantic
from pydantic import BaseModel

from app import env

logger = logging.getLogger(__name__)


class BinderBuildEvent(BaseModel):
    phase: str | None = None
    message: str | None = None
    imageName: str | None = None


async def stream_binder_build(binder_ref: str) -> AsyncGenerator[
        Tuple[str, BinderBuildEvent | None], None]:
    """
    Proxies the Binder SSE stream to the caller, then upserts the catalogue.
    """
    binder_build_url = f"{env.BINDER_URL}/build/{binder_ref}"
    logger.info(f"Building {binder_build_url}")
    headers = {
        "Accept": "text/event-stream",
        "Authorization": f"Bearer {env.BINDER_API_TOKEN}",
        }
    try:
        async with httpx.AsyncClient(
                timeout=None, verify=env.VERIFY_SSL
                ) as client:
            async with client.stream(
                    "GET", binder_build_url, headers=headers
                    ) as response:
                response.raise_for_status()

                async for raw_message in response.aiter_lines():
                    logger.debug(f"Binder SSE: {raw_message}")

                    # Parse data messages
                    if raw_message.startswith("data:"):
                        payload = raw_message[len("data:"):].strip()
                    # Forward other messages unmodified to the client
                    else:
                        yield raw_message + "\n", None
                        continue

                    try:
                        parsed_event = BinderBuildEvent.model_validate_json(
                            payload
                            )
                    except pydantic.ValidationError:
                        logger.warning(f"Could not parse SSE line: "
                                       f"{raw_message}")
                        yield raw_message + "\n", None
                        continue

                    yield raw_message + "\n", parsed_event

                    if parsed_event.phase == "failed":
                        logger.error(
                            f"Binder build failed for {binder_ref}: "
                            f"{parsed_event.message}"
                            )
                        return

                    if parsed_event.phase == "built":
                        logger.info(
                            f"Binder build complete for {binder_ref}. "
                            f"Image: {parsed_event.imageName}"
                            )
                        # Stop listening after phase=built (binderhub may
                        # attempt to launch the image afterward, but we don't
                        # care)
                        return

    except httpx.HTTPStatusError as exc:
        msg = f"Binder build request failed ({binder_ref}): {exc}"
        logger.error(msg)
        yield (f"data: {json.dumps({'phase': 'failed', 'message': msg})}\n\n",
               None)
        return
    except Exception as exc:
        msg = f"Unexpected error watching Binder build for {binder_ref}: {exc}"
        logger.exception(msg)
        yield (f"data: {json.dumps({'phase': 'failed', 'message': msg})}\n\n",
               None)
        return
