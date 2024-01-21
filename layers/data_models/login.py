"""Login data models."""
from pydantic import BaseModel


class AuthenticationRequest(BaseModel):
    """Authentication request model"""

    user: str
    authcode: str


class AuthorizationRequest(BaseModel):
    """Authorization request model"""

    token: str


class LoginResponse(BaseModel):
    """Login response model"""

    access_token: str


if __name__ == "__main__":
    print(LoginResponse(access_token="jwt_token").model_dump_json())
