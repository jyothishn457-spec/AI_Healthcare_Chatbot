"""
auth.py
Authentication helpers: PBKDF2 password hashing and JWT access tokens.

The hashing uses only Python's standard library (no extra dependency),
while tokens are issued with PyJWT.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Hash a password with a random salt, returned as 'salt$hash'."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Compare a plaintext password against a stored 'salt$hash' value."""
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    # compare_digest avoids timing attacks on the comparison
    return secrets.compare_digest(digest.hex(), expected)


def create_access_token(user_id: int, username: str, is_admin: bool) -> str:
    """Create a signed JWT that identifies a logged-in user."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "is_admin": bool(is_admin),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Validate a JWT and return its payload."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract and validate the Bearer token.

    Returns the user dict (from the database) for the authenticated request.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")

    payload = decode_token(auth[7:])

    # Import here to keep the module dependency graph simple.
    from database import get_user_by_id

    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def require_admin(user: dict = get_current_user) -> dict:
    """FastAPI dependency: allow only admin users through."""
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
