from datetime import datetime, timedelta

import jwt

if __name__ == "__main__":
    expire = datetime.utcnow() + timedelta(minutes=60)

    payload = {
        "expire": expire.strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": "id-principal",
    }
    secret = "27d621e9bc55e6c659842904982abf06d89123c844e4d8bc62060ccd6536c360"
    encoded = jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )
    print(encoded)
