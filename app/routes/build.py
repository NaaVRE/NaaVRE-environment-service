from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..services.binder import stream_binder_build

router = APIRouter()


@router.post(
    "/build/gh/{org}/{repo}/{ref}",
    summary="Trigger a Binder build for a GitHub repository",
    )
async def trigger_binder_build(
        org: str, repo: str, ref: str
        ) -> StreamingResponse:
    """
    Triggers a build on Binder for `gh/{org}/{repo}/{ref}`.

    Streams the Binder SSE events back to the client. Once the build
    completes upserts the record to the catalogue.
    """
    binder_ref = f"gh/{org}/{repo}/{ref}"

    return StreamingResponse(
        stream_binder_build(binder_ref),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            },
        )
