from pydantic import BaseModel


class TokenAuthMethod(BaseModel):
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
