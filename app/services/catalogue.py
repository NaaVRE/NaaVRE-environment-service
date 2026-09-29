import logging

import httpx
from pydantic import BaseModel

from app import env

logger = logging.getLogger(__name__)


class APIListResponse[T](BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[T]


class BinderEnvironmentResponse(BaseModel):
    url: str
    binder_ref: str
    container_image: str | None = None
    pre_pull: bool


async def get_pre_pull_environments() -> list[BinderEnvironmentResponse]:
    """ Retrieve all BinderEnvironment records flagged for pre-pulling """
    catalogue_base = f"{env.CATALOGUE_URL}/binder-environments/"

    results: list[BinderEnvironmentResponse] = []

    async with httpx.AsyncClient(verify=env.VERIFY_SSL) as client:
        url = catalogue_base
        while url is not None:
            resp = await client.get(
                url,
                params={"pre_pull": "true"},
                )
            resp.raise_for_status()
            page = APIListResponse[BinderEnvironmentResponse].model_validate(
                resp.json()
                )
            results.extend(page.results)
            url = page.next

    return results


async def upsert_binder_environment(
        binder_ref: str,
        container_image: str,
        ) -> None:
    """ Create or update a BinderEnvironment record in the catalogue """
    catalogue_base = f"{env.CATALOGUE_URL}/binder-environments/"

    async with httpx.AsyncClient(verify=env.VERIFY_SSL) as client:
        # Check whether a record already exists.
        try:
            get_resp = await client.get(
                catalogue_base, params={"binder_ref": binder_ref}
                )
            get_resp.raise_for_status()
            existing_records = APIListResponse[
                BinderEnvironmentResponse].model_validate(get_resp.json())
        except Exception as exc:
            logger.exception(f"catalogue GET failed for {binder_ref}: {exc}")
            return

        new_record_payload = {
            "binder_ref": binder_ref,
            "container_image": container_image,
            }
        headers = {
            "Authorization": f"Token {env.CATALOGUE_API_TOKEN}",
            }

        # If no record exists, create one
        if existing_records.count == 0:
            try:
                post_resp = await client.post(
                    catalogue_base,
                    json=new_record_payload,
                    headers=headers,
                    )
                post_resp.raise_for_status()
                logger.info(f"catalogue record created for {binder_ref}")
            except Exception as exc:
                logger.exception(
                    f"catalogue creation failed for {binder_ref}: {exc}"
                    )

        # If one record exist, update it
        elif existing_records.count == 1:
            existing_record = existing_records.results[0]
            try:
                put_resp = await client.put(
                    existing_record.url,
                    json=new_record_payload,
                    headers=headers,
                    )
                put_resp.raise_for_status()
                logger.info(f"catalogue updated for {binder_ref}")
            except Exception as exc:
                logger.exception(
                    f"catalogue update failed for {binder_ref}: {exc}"
                    )

        # Having more than one record should be impossible, because binder_ref
        # is unique in the catalogue.
        else:
            logger.exception(
                f"The catalogue has {existing_records.count} items for "
                f"{binder_ref}. This should not be possible."
                )
