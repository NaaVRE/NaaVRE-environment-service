from typing import Annotated
import logging

from fastapi import APIRouter, Depends

from ..dependencies import require_auth
from ..models.auth import User

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/me")
def protected_route(user: Annotated[User, Depends(require_auth)]) -> dict:
    return {"user": {"id": user.id}}
