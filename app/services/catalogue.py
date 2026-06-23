import logging

from app import config
import httpx

logger = logging.getLogger(__name__)


async def upsert_catalogue(binder_ref: str, docker_image: str) -> None:
    """Create or update the binder-env record in the catalogue service."""
    catalogue_base = f"{config.CATALOGUE_URL}/binder-envs"

    async with httpx.AsyncClient() as client:
        # Check whether a record already exists.
        try:
            get_resp = await client.get(
                catalogue_base, params={"binder_ref": binder_ref}
                )
            get_resp.raise_for_status()
            results = get_resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"catalogue GET failed for {binder_ref}: {exc}")
            return

        payload = {"binder_ref": binder_ref, "docker_image": docker_image}

        # If a record exists update it
        if results:
            existing = results[0]  # uniquely identified by binder_ref
            record_id = existing.get("id", binder_ref)
            try:
                put_resp = await client.put(
                    f"{catalogue_base}/{record_id}", json=payload
                    )
                put_resp.raise_for_status()
                logger.info(f"catalogue updated for {binder_ref}")
            except Exception as exc:  # noqa: BLE001
                logger.exception(f"catalogue PUT failed for {binder_ref}: {exc}")

        # If no record create one
        else:
            try:
                post_resp = await client.post(catalogue_base, json=payload)
                post_resp.raise_for_status()
                logger.info(f"catalogue record created for {binder_ref}")
            except Exception as exc:
                logger.exception(f"catalogue POST failed for {binder_ref}: {exc}")
