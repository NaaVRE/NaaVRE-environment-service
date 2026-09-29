from typing import Annotated
import logging

from fastapi import APIRouter, Depends

from ..dependencies import require_auth
from ..models.auth import User
from ..services.catalogue import get_pre_pull_environments
from ..services.k8s import DaemonsetSyncResult, sync_image_puller_daemonset

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "/image-puller/sync",
    summary="Sync the image-puller DaemonSet with the catalogue",
    )
async def sync_image_puller(
        user: Annotated[User, Depends(require_auth)]
        ) -> DaemonsetSyncResult:
    """ Sync the image-puller DaemonSet with the environments flagged
    `pre_pull` in the catalogue.
    """
    environments = await get_pre_pull_environments()

    logger.info(
        f"Syncing image-puller daemonset with {len(environments)} "
        "environment(s)"
        )

    return await sync_image_puller_daemonset(environments)
