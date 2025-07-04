import jwt
from datetime import datetime, timedelta, timezone
import os
from calendar import timegm

from data_models import User

DEFAULT_SECRET_KEY = "27d621e9bc55e6c659842904982abf06d89123c844e4d8bc62060ccd6536c360"
SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)


def datetime_to_epoch(dt: datetime) -> int:
    return timegm(dt.utctimetuple())


def aware_utcnow(use_tz=False) -> datetime:
    dt = datetime.now(tz=timezone.utc)
    if not use_tz:
        dt = dt.replace(tzinfo=None)

    return dt


class Token:
    secret_key = SECRET_KEY
    lifetime = timedelta(minutes=5)

    def __init__(self, token=None):
        self._token = token
        if token:
            self.validate_jwt_token()
        self._exp = aware_utcnow() + self.lifetime
        self._jwt_payload = {"exp": self.get_exp()}

    def get_exp(self):
        return datetime_to_epoch(self._exp)

    def set_exp(self, value):
        self._jwt_payload["exp"] = value

    def get_access_token(self, user: User):
        self._jwt_payload["user_id"] = user.principal

        encoded = jwt.encode(
            self._jwt_payload,
            self.secret_key,
            algorithm="HS256",
        )
        return encoded

    def validate_jwt_token(self):
        raise NotImplementedError("Must implement validate_jwt_token")
    
    def decode_jwt_token(self, authorization_header):
        try:
            if not authorization_header or not authorization_header.startswith('Bearer '):
                raise ValueError("Invalid authorization header")
        
            token = authorization_header.replace('Bearer ', '')
            decoded = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return decoded.get("user_id")
        except Exception as e:
            print(f"Error extracting user_id from token: {str(e)}")
            raise ValueError("Invalid token")


class AccessToken(Token):
    lifetime = timedelta(minutes=60)


if __name__ == "__main__":
    user = User(principal="test_user")

    token = AccessToken(token=None)
    jwt_token = token.get_access_token(user)

    print(jwt_token)
