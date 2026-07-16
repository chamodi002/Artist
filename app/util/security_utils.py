from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.config.security import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# APIKeyHeader setup for Swagger UI input matching 'Authorization' header
oauth2_scheme = APIKeyHeader(
    name="Authorization", 
    description="Enter token as: Bearer <your_jwt_token>",
    auto_error=False  
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against its hashed version."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(username: Optional[str] = None, data: dict = None):
    """
    Creates a JWT token. Supports both signatures:
    - create_access_token(username="admin")
    - create_access_token(data={"sub": "admin", "role": "admin"})
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    if data and isinstance(data, dict):
        payload = data.copy()
        if "exp" not in payload:
            payload["exp"] = expire
    else:
        payload = {
            "sub": username,
            "role": "admin",
            "exp": expire
        }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def get_current_admin(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Main dependency to verify the admin token.
    Extracts Bearer scheme and validates the payload seamlessly.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header/token"
        )

    if isinstance(token, str) and (token.startswith("Bearer ") or token.startswith("bearer ")):
        try:
            token = token.split(" ")[1]
        except IndexError:
            raise HTTPException(
                status_code=401,
                detail="Invalid Authorization header format. Use 'Bearer <token>'"
            )

    try:
        # JWT Decode logic with verify_exp turned off for local testing
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False}
        )

        username = payload.get("sub")
        role = payload.get("role")

        if username is None or role != "admin":
            raise HTTPException(
                status_code=401,
                detail="Could not validate admin credentials"
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate admin credentials"
        )


# Aliasing verify_admin_token to get_current_admin to support both names dynamically
verify_admin_token = get_current_admin