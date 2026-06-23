from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from ..services.binder import watch_binder_and_sync_catalogue

router = APIRouter()


class BuildAccepted(BaseModel):
    binder_ref: str
    message: str


@router.post(
    "/build/gh/{org}/{repo}/{ref}",
    response_model=BuildAccepted,
    status_code=202,
    summary="Trigger a Binder build for a GitHub repository",
    )
async def trigger_binder_build(
        org: str,
        repo: str,
        ref: str,
        background_tasks: BackgroundTasks,
        ) -> BuildAccepted:
    """
    Triggers a build on Binder for `gh/{org}/{repo}/{ref}`.

    Returns immediately with the `binder_ref` the client can use to track
    the build.  A background task watches the Binder SSE stream and, once
    the build completes, upserts the record in the catalogue service.
    """
    binder_ref = f"gh/{org}/{repo}/{ref}"

    # Fire-and-forget: watch the stream and sync the catalogue once done.
    background_tasks.add_task(
        watch_binder_and_sync_catalogue,
        binder_ref,
        )

    return BuildAccepted(
        binder_ref=binder_ref,
        message="Build triggered. Use binder_ref to check status.",
        )
