from typing import List

from pydantic_settings import BaseSettings

from .auth import User


class Configuration(BaseSettings):
    users: List[User]
