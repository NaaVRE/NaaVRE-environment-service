from collections.abc import AsyncGenerator
import json
import logging

from app import config
from app.services.catalogue import upsert_catalogue
import httpx

logger = logging.getLogger(__name__)


async def stream_binder_build(binder_ref: str) -> AsyncGenerator[str, None]:
    """
    Proxies the Binder SSE stream to the caller, then upserts the catalogue.

    Yields raw SSE lines (forwarded verbatim to the client). After the stream
    ends — whether by completion, failure, or error — the catalogue is updated
    if an image name was received.
    """
    binder_build_url = f"{config.BINDER_URL}/build/{binder_ref}"
    logger.info(f"Building {binder_build_url}")
    headers = {
        "Accept": "text/event-stream",
        "Authorization": f"Bearer {config.BINDER_API_TOKEN}",
        }
    image_name: str | None = None

    try:
        async with httpx.AsyncClient(
                timeout=None, verify=config.VERIFY_SSL
                ) as client:
            async with client.stream(
                    "GET", binder_build_url, headers=headers
                    ) as response:
                response.raise_for_status()

                async for raw_line in response.aiter_lines():
                    logger.debug(f"Binder SSE: {raw_line}")

                    # Forward every line to the client (including heartbeats/comments).
                    yield raw_line + "\n"

                    # Skip non-data lines for internal processing.
                    if not raw_line or raw_line.startswith(":"):
                        continue

                    if raw_line.startswith("data:"):
                        payload = raw_line[len("data:"):].strip()
                    else:
                        continue

                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse SSE line: {raw_line}")
                        continue

                    phase = event.get("phase")

                    if phase == "failed":
                        logger.error(
                            "Binder build failed for %s: %s",
                            binder_ref,
                            event.get("message"),
                            )
                        return  # nothing to sync

                    if phase == "built":
                        image_name = event.get("imageName")
                        logger.info(
                            "Binder build complete for %s — image: %s",
                            binder_ref,
                            image_name,
                            )

    except httpx.HTTPStatusError as exc:
        msg = f"Binder build request failed ({binder_ref}): {exc}"
        logger.error(msg)
        yield f"data: {json.dumps({'phase': 'failed', 'message': msg})}\n\n"
        return
    except Exception as exc:
        msg = f"Unexpected error watching Binder build for {binder_ref}: {exc}"
        logger.exception(msg)
        yield f"data: {json.dumps({'phase': 'failed', 'message': msg})}\n\n"
        return

    if not image_name:
        logger.warning(
            "No imageName received for %s; skipping catalogue sync.",
            binder_ref
            )
        return

    await upsert_catalogue(binder_ref, image_name)
