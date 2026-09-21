from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import env
from app.models.auth import User
from app.models.configuration import Configuration

_bearer = HTTPBearer()


@lru_cache(maxsize=1)
def load_config() -> Configuration:
    with open(env.CONFIG_FILE_PATH) as f:
        return Configuration.model_validate_json(f.read())


def require_auth(
        credentials: Annotated[
            HTTPAuthorizationCredentials, Security(_bearer)],
        config: Annotated[Configuration, Depends(load_config)],
        ) -> User:

    token = credentials.credentials
    for user in config.users:
        if user.authenticate_token(token):
            return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
        )
