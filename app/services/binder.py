import json
import logging

from app import config
from app.services.catalogue import upsert_catalogue
import httpx

logger = logging.getLogger(__name__)


async def watch_binder_and_sync_catalogue(
        binder_ref: str,
        ) -> None:
    """
    Consumes the Binder SSE stream until the build completes or fails,
    then upserts the record in the catalogue.
    """
    binder_build_url = f"{config.BINDER_URL}/build/{binder_ref}"
    logger.info(f"Building {binder_build_url}")
    headers = {
        "Accept": "text/event-stream",
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
                    # SSE lines look like:  data: {...}
                    # Comment/heartbeat lines look like:  :heartbeat  — skip them.
                    if not raw_line or raw_line.startswith(":"):
                        continue

                    if raw_line.startswith("data:"):
                        payload = raw_line[len("data:"):].strip()
                    else:
                        continue

                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Binder SSE: could not parse line: %s", raw_line
                            )
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
                        # We have what we need; we can stop consuming the stream.
                        break

    except httpx.HTTPStatusError as exc:
        logger.error("Binder build request failed (%s): %s", binder_ref, exc)
        return
    except Exception as exc:
        logger.exception(
            "Unexpected error watching Binder build for %s: %s", binder_ref,
            exc
            )
        return

    if not image_name:
        logger.warning(
            "No imageName received for %s; skipping catalogue sync.",
            binder_ref
            )
        return

    await upsert_catalogue(binder_ref, image_name)
