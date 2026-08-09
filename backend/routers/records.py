"""
routers/records.py
Medical History and Prescriptions CRUD.

Every query filters by the authenticated user id on the server side, so a
user can never read or modify another user's records.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import database
from auth import get_current_user

router = APIRouter(prefix="/records", tags=["records"])

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


# ---------------------------------------------------------------- medical history
class HistoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    event_date: str = Field(pattern=DATE_PATTERN, description="YYYY-MM-DD")


class HistoryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    event_date: str | None = Field(default=None, pattern=DATE_PATTERN)


@router.get("/history")
def list_history(user=Depends(get_current_user)):
    """Return the user's medical history timeline."""
    return {"history": database.list_history(user["id"])}


@router.post("/history")
def create_history(body: HistoryCreate, user=Depends(get_current_user)):
    """Add a medical-history entry."""
    entry_id = database.add_history_entry(
        user["id"], body.title.strip(), body.description.strip(), body.event_date
    )
    return {"entry": database.get_history_entry(entry_id, user["id"])}


@router.patch("/history/{entry_id}")
def update_history(entry_id: int, body: HistoryUpdate, user=Depends(get_current_user)):
    """Edit a medical-history entry."""
    fields = body.model_dump(exclude_unset=True)
    if not database.update_history_entry(entry_id, user["id"], fields):
        raise HTTPException(status_code=404, detail="History entry not found")
    return {"entry": database.get_history_entry(entry_id, user["id"])}


@router.delete("/history/{entry_id}")
def delete_history(entry_id: int, user=Depends(get_current_user)):
    """Delete a medical-history entry."""
    if not database.delete_history_entry(entry_id, user["id"]):
        raise HTTPException(status_code=404, detail="History entry not found")
    return {"status": "deleted"}


# ---------------------------------------------------------------- prescriptions
class PrescriptionCreate(BaseModel):
    medication: str = Field(min_length=1, max_length=200)
    dosage: str = Field(default="", max_length=200)
    frequency: str = Field(default="", max_length=200)
    prescriber: str = Field(default="", max_length=120)
    start_date: str = Field(pattern=DATE_PATTERN, description="YYYY-MM-DD")
    notes: str = Field(default="", max_length=1000)
    active: bool = True


class PrescriptionUpdate(BaseModel):
    medication: str | None = Field(default=None, max_length=200)
    dosage: str | None = Field(default=None, max_length=200)
    frequency: str | None = Field(default=None, max_length=200)
    prescriber: str | None = Field(default=None, max_length=120)
    start_date: str | None = Field(default=None, pattern=DATE_PATTERN)
    notes: str | None = Field(default=None, max_length=1000)
    active: bool | None = None


@router.get("/prescriptions")
def list_prescriptions(active: bool | None = None, user=Depends(get_current_user)):
    """Return the user's prescriptions (optionally active only)."""
    active_only = True if active else False
    return {"prescriptions": database.list_prescriptions(user["id"], active_only)}


@router.post("/prescriptions")
def create_prescription(body: PrescriptionCreate, user=Depends(get_current_user)):
    """Add a prescription record."""
    prescription_id = database.add_prescription(
        user["id"],
        body.medication.strip(),
        body.dosage.strip(),
        body.frequency.strip(),
        body.prescriber.strip(),
        body.start_date,
        body.notes.strip(),
        body.active,
    )
    return {"prescription": database.get_prescription(prescription_id, user["id"])}


@router.patch("/prescriptions/{prescription_id}")
def update_prescription(
    prescription_id: int, body: PrescriptionUpdate, user=Depends(get_current_user)
):
    """Edit a prescription (e.g. mark as inactive when finished)."""
    fields = body.model_dump(exclude_unset=True)
    if not database.update_prescription(prescription_id, user["id"], fields):
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"prescription": database.get_prescription(prescription_id, user["id"])}


@router.delete("/prescriptions/{prescription_id}")
def delete_prescription(prescription_id: int, user=Depends(get_current_user)):
    """Delete a prescription record."""
    if not database.delete_prescription(prescription_id, user["id"]):
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"status": "deleted"}
