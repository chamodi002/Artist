from jose import jwt
from datetime import datetime, timedelta, timezone
import os


SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "temporary-secret-key"
)

ALGORITHM = "HS256"


def create_access_token(data: dict):

    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=60
    )

    payload["exp"] = expire


    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token