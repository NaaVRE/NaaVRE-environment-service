from typing import Annotated
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing_extensions import AsyncGenerator

from ..dependencies import require_auth
from ..models.auth import User
from ..services.binder import BinderBuildEvent, stream_binder_build
from ..services.catalogue import upsert_binder_environment

router = APIRouter()

logger = logging.getLogger(__name__)


async def build_env(binder_ref: str) -> AsyncGenerator[str, None]:
    parsed_event: BinderBuildEvent | None = None
    async for raw_message, parsed_event in stream_binder_build(binder_ref):
        yield raw_message

    image_name = parsed_event.imageName if parsed_event else None
    if image_name:
        await upsert_binder_environment(binder_ref, image_name)
    else:
        logger.warning(
            "No imageName received for {binder_ref}. "
            "Skipping catalogue upsert."
            )


@router.post(
    "/build/gh/{org}/{repo}/{ref}",
    summary="Trigger a Binder build for a GitHub repository",
    )
async def trigger_binder_build(
        org: str, repo: str, ref: str,
        user: Annotated[User, Depends(require_auth)]
        ) -> StreamingResponse:
    """
    Triggers a build on Binder for `gh/{org}/{repo}/{ref}`.

    Streams the Binder SSE events back to the client. Once the build
    completes upserts the record to the catalogue.
    """
    binder_ref = f"gh/{org}/{repo}/{ref}"

    return StreamingResponse(
        build_env(binder_ref),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            },
        )
