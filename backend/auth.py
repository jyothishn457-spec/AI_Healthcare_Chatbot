"""
auth.py
Authentication helpers: PBKDF2 password hashing, JWT access tokens and
revocable refresh tokens.

  - Access tokens are short-lived JWTs sent in the Authorization header.
  - Refresh tokens are long-lived random secrets, stored hashed in the DB
    so they can be revoked on logout and rotated on every refresh.

The hashing uses only Python's standard library (no extra dependency),
while access tokens are issued with PyJWT.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
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


# ---------------------------------------------------------------- access tokens
def create_access_token(user_id: int, username: str, is_admin: bool) -> str:
    """Create a signed JWT that identifies a logged-in user."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "is_admin": bool(is_admin),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Validate a JWT and return its payload."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


# ---------------------------------------------------------------- refresh tokens
def create_refresh_token(user_id: int) -> str:
    """Create a refresh token, store its hash, and return the raw token.

    The raw token is shown to the client once; only the SHA-256 hash is kept
    in the database so a leaked DB cannot be used to mint new sessions.
    """
    raw = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    # Import here to keep the module dependency graph simple.
    from database import store_refresh_token

    store_refresh_token(user_id, _hash_token(raw), expires_at.isoformat())
    return raw


def verify_refresh_token(raw: str) -> dict:
    """Validate a refresh token and return the owning user.

    Raises 401 when the token is unknown, revoked or expired.
    """
    from database import get_refresh_token, get_user_by_id

    record = get_refresh_token(_hash_token(raw))
    if not record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    user = get_user_by_id(record["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def revoke_refresh_token(raw: str) -> None:
    """Delete a refresh token so it can no longer be used."""
    from database import delete_refresh_token

    delete_refresh_token(_hash_token(raw))


def revoke_all_refresh_tokens(user_id: int) -> None:
    """Delete every refresh token belonging to a user."""
    from database import delete_all_refresh_tokens

    delete_all_refresh_tokens(user_id)


def _hash_token(raw: str) -> str:
    """SHA-256 of a raw refresh token (stored value / lookup key)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- dependencies
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
