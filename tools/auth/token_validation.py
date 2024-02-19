from data_models import User
from shared.auth.tokens import AccessToken

if __name__ == "__main__":
    token = AccessToken()

    jwt = token.get_access_token(user=User(principal="temp"))

    print(jwt)
