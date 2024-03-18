"""Authentication backends.

Base class for Authentication backends and implementations for
Elna auth backend
"""
import os

from data_models import User, AuthenticationRequest
from ic.client import Client
from ic.identity import Identity
from ic.agent import Agent
from ic.candid import encode, Types
from .tokens import AccessToken


class AuthBackendBase:
    """Base class for authentication backends"""

    def authenticate(self, request: AuthenticationRequest) -> User:
        """Authenticate the request and returns an authenticated User"""

        raise NotImplementedError("authenticate not implemented")

    def authenticate_with_token(self, token: str) -> bool:
        """Authenticate user using jwt token and return status"""
        raise NotImplementedError("authenticate_with_token not implemented")

    def get_access_token(self, user: User) -> str:
        """Get the access for the given user"""
        raise NotImplementedError("get_access_token not implemented")

    def get_refresh_token(self, user: User, token: str) -> str:
        """Get the refresh token for the given user"""
        raise NotImplementedError("get_refresh_token not implemented")


class ElanaAuthBackend(AuthBackendBase):
    """Authentication backend with Elna ICP Canister"""

    def __init__(self, url: str, auth_canister: str, auth_function: str):
        self._url = url
        self._identity = Identity()
        self._client = Client(url=self._url)
        self._icp_agent = Agent(self._identity, self._client)
        self._auth_canister = auth_canister
        self._canister_auth_func = auth_function

    def authenticate(self, login_request: AuthenticationRequest) -> User:
        """Authenticate the request and returns an authenticated User"""
        encoded_args = encode(
            [
                {
                    "type": Types.Principal,
                    "value": login_request.user,
                }
            ]
        )

        self._icp_agent.update_raw(
            self._auth_canister, self._canister_auth_func, encoded_args
        )

        return User(principal=login_request.user)

    def authenticate_with_token(self, token: str):
        """Authenticate user using jwt token and return status"""
        print("token : ", token)
        AccessToken(token_string=token)

    def get_access_token(self, user: User) -> str:
        """Get the access for the given user"""
        token = AccessToken()
        return token.get_access_token(user)


elna_auth_backend = ElanaAuthBackend(
    url="https://ic0.app",
    auth_canister=os.environ.get("CANISTER_ID"),
    auth_function="getUserToken",
)

if __name__ == "__main__":
    auth_backend = ElanaAuthBackend(
        url="https://ic0.app",
        auth_canister="6qy4q-5aaaa-aaaah-adwma-cai",
        auth_function="getUserToken",
    )

    request = AuthenticationRequest(
        user="4cay5-ew3bs-vr6yl-7iffu-67doc-l655v-dluy7-qplpx-7pkio-er5rt-uqe",
        authcode="",
    )
    user = auth_backend.authenticate(request)
    print(user)
