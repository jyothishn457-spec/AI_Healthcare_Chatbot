"""
routers/appointments.py
Appointment booking and management.

Status flow: pending -> confirmed -> completed, with 'cancelled' allowed at
any point. All operations are scoped to the authenticated user server-side.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import database
from auth import get_current_user

router = APIRouter(prefix="/appointments", tags=["appointments"])

VALID_STATUSES = {"pending", "confirmed", "completed", "cancelled"}

# Demo doctor/specialty catalogue surfaced to the booking form.
DOCTORS = [
    {"name": "Dr. Priya Sharma", "specialty": "General Medicine"},
    {"name": "Dr. Rajesh Kumar", "specialty": "Cardiology"},
    {"name": "Dr. Ananya Iyer", "specialty": "Pediatrics"},
    {"name": "Dr. Meera Nair", "specialty": "Dermatology"},
    {"name": "Dr. Arun Menon", "specialty": "Orthopedics"},
    {"name": "Dr. Kavitha Rao", "specialty": "Gynecology"},
    {"name": "Dr. Suresh Babu", "specialty": "Neurology"},
    {"name": "Dr. Lakshmi Devi", "specialty": "ENT"},
]


class AppointmentCreate(BaseModel):
    doctor_name: str = Field(min_length=1, max_length=120)
    specialty: str = Field(min_length=1, max_length=80)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    time: str = Field(pattern=r"^\d{2}:\d{2}$", description="HH:MM (24h)")
    notes: str = Field(default="", max_length=1000)


class AppointmentUpdate(BaseModel):
    doctor_name: str | None = Field(default=None, max_length=120)
    specialty: str | None = Field(default=None, max_length=80)
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    notes: str | None = Field(default=None, max_length=1000)
    status: str | None = None


@router.get("/doctors")
def doctors():
    """List the available doctors/specialties for the booking form."""
    return {"doctors": DOCTORS}


@router.post("")
def create_appointment(body: AppointmentCreate, user=Depends(get_current_user)):
    """Book a new appointment (starts in 'pending' status)."""
    appointment_id = database.create_appointment(
        user["id"],
        body.doctor_name.strip(),
        body.specialty.strip(),
        body.date,
        body.time,
        body.notes.strip(),
    )
    appointment = database.get_appointment(appointment_id, user["id"])
    return {"appointment": appointment}


@router.get("")
def list_appointments(
    status: str | None = None,
    upcoming: bool = False,
    user=Depends(get_current_user),
):
    """List the user's appointments, optionally filtered by status."""
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status filter")
    return {"appointments": database.list_appointments(user["id"], status, upcoming)}


@router.patch("/{appointment_id}")
def update_appointment(
    appointment_id: int, body: AppointmentUpdate, user=Depends(get_current_user)
):
    """Reschedule, update notes, or change status of an appointment."""
    fields = body.model_dump(exclude_unset=True)
    if "status" in fields and fields["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status value")

    if not database.update_appointment(appointment_id, user["id"], fields):
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"appointment": database.get_appointment(appointment_id, user["id"])}


@router.delete("/{appointment_id}")
def cancel_appointment(appointment_id: int, user=Depends(get_current_user)):
    """Cancel (delete) an appointment."""
    if not database.delete_appointment(appointment_id, user["id"]):
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"status": "cancelled"}
