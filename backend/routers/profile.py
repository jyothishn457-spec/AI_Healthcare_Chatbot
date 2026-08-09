"""
routers/profile.py
Profile and settings: read/update profile, notification preferences, and
account deletion.

Account deletion is destructive and requires the password to be confirmed.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import database
from auth import (
    get_current_user,
    hash_password,
    revoke_all_refresh_tokens,
    verify_password,
)
from database import DEFAULT_NOTIFICATION_PREFS

router = APIRouter(prefix="/profile", tags=["profile"])

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ALLOWED_GENDERS = {"male", "female", "non-binary", "prefer not to say"}
ALLOWED_NOTIF_KEYS = set(DEFAULT_NOTIFICATION_PREFS)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    gender: str | None = Field(default=None, max_length=30)
    notification_prefs: dict | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


def _validate_email(email: str) -> str:
    """Return a stripped, lower-cased email or raise a 422."""
    email = email.strip().lower()
    if email and not EMAIL_PATTERN.match(email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address")
    return email


@router.get("")
def get_profile(user=Depends(get_current_user)):
    """Return the current user's profile (never includes the password hash)."""
    return {"profile": user}


@router.patch("")
def update_profile(body: ProfileUpdate, user=Depends(get_current_user)):
    """Update profile fields, notification preferences and/or password."""
    fields = body.model_dump(exclude_unset=True)

    if "email" in fields:
        fields["email"] = _validate_email(fields["email"] or "")
    if "gender" in fields and fields["gender"] not in ALLOWED_GENDERS:
        raise HTTPException(status_code=422, detail="Invalid gender option")

    if "notification_prefs" in fields:
        prefs = fields["notification_prefs"] or {}
        unknown = set(prefs) - ALLOWED_NOTIF_KEYS
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown preference keys: {', '.join(sorted(unknown))}"
            )
        merged = dict(DEFAULT_NOTIFICATION_PREFS)
        merged.update(prefs)
        fields["notification_prefs"] = {k: bool(v) for k, v in merged.items()}

    # Password changes are stored hashed; never return or log the plaintext.
    if "password" in fields and fields["password"]:
        fields.pop("password")  # the DB profile update ignores this column
        database.update_user_password(user["id"], hash_password(body.password))
        revoke_all_refresh_tokens(user["id"])

    database.update_user_profile(user["id"], fields)
    return {"profile": database.get_user_by_id(user["id"])}


@router.delete("")
def delete_account(body: DeleteAccountRequest, user=Depends(get_current_user)):
    """Permanently delete the account (confirms the password first)."""
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    revoke_all_refresh_tokens(user["id"])
    database.delete_user(user["id"])
    return {"status": "deleted"}
