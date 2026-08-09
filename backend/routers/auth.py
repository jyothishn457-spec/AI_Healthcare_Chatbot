"""
routers/auth.py
Authentication endpoints: register, login, logout and token refresh.

Login returns a short-lived access token (JWT) plus a long-lived, revocable
refresh token. The refresh endpoint rotates the refresh token (old one is
revoked, a new one is issued) so a stolen token has a limited lifetime.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import database
from auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    verify_password,
    verify_refresh_token,
)
from ratelimit import rate_limit

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=256)


def _auth_response(user: dict) -> dict:
    """Build the shared login/register/refresh response shape."""
    access_token = create_access_token(user["id"], user["username"], bool(user["is_admin"]))
    return {
        # Newer field names plus the legacy "token" alias for compatibility.
        "access_token": access_token,
        "refresh_token": create_refresh_token(user["id"]),
        "user": _public_user(user),
    }


def _public_user(user: dict) -> dict:
    """Strip the password hash from a user row before returning it."""
    return {k: v for k, v in user.items() if k != "password_hash"}


@router.post("/register")
def register(body: RegisterRequest):
    """Create a new user account and return tokens (auto-login)."""
    username = body.username.strip()
    if database.get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username already taken")

    user_id = database.create_user(username, hash_password(body.password), is_admin=False)
    user = database.get_user_by_id(user_id)
    return _auth_response(user)


@router.post("/login")
def login(body: LoginRequest, request: Request):
    """Authenticate a user and return access + refresh tokens."""
    rate_limit(request)
    user = database.get_user_by_username(body.username.strip())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return _auth_response(user)


@router.post("/refresh")
def refresh(body: RefreshRequest):
    """Exchange a valid refresh token for a fresh pair (rotation)."""
    user = verify_refresh_token(body.refresh_token)
    revoke_refresh_token(body.refresh_token)  # rotate: old token dies here
    return _auth_response(user)


@router.post("/logout")
def logout(body: RefreshRequest | None = None, user=Depends(get_current_user)):
    """Revoke the user's refresh token(s) and end the session."""
    if body and body.refresh_token:
        # Best effort: revoke the specific token if it is valid.
        try:
            revoke_refresh_token(body.refresh_token)
        except HTTPException:
            pass
    else:
        revoke_all_refresh_tokens(user["id"])
    return {"status": "logged_out"}
