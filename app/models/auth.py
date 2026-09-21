from typing import Literal

from pydantic import BaseModel


class TokenAuthMethod(BaseModel):
    method: Literal["token"]
    token: str

    def verify(self, token: str) -> bool:
        return self.token == token


class User(BaseModel):
    id: str
    auth: list[TokenAuthMethod]

    def authenticate_token(self, token: str) -> bool:
        return any(
            method.verify(token)
            for method in self.auth
            if isinstance(method, TokenAuthMethod)
            )
