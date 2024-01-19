from pydantic import BaseModel


class AuthenticationRequest(BaseModel):
    user: str
    authcode: str


class AuthorizationRequest(BaseModel):
    token: str


class LoginResponse(BaseModel):
    access_token: str
