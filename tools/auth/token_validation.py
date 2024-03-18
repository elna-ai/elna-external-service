from data_models import User
from shared.auth.tokens import AccessToken

if __name__ == "__main__":
    user = User(principal="test_user")

    token = AccessToken(token_string=None)
    generated_jwt_token = token.get_access_token(user)
    print("Generated JWT: ", generated_jwt_token)

    given_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDg1MjQwMTUsInVzZXJfaWQiOiJ0ZXN0X3VzZXIifQ.MKs5YUVl68xyeWrM2ygyqfvgmTjsudrAaWW3M1BfD0E"
    AccessToken(token_string=given_jwt_token)
