"""
routers/prediction.py
Structured symptom intake -> ranked possible conditions.

Takes a checklist of symptom ids (not free text), scores them against the
knowledge base in prediction.py and persists each run so the user has a
reviewable history. Results are always flagged as informational.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import database
import prediction
from auth import get_current_user

router = APIRouter(prefix="/predict", tags=["prediction"])

ALLOWED_AGE_GROUPS = {"child", "teen", "adult", "senior"}
ALLOWED_SEXES = {"male", "female", "other", "prefer not to say"}
ALLOWED_DURATIONS = {"less_than_24h", "1_3_days", "3_7_days", "over_week"}


class PredictRequest(BaseModel):
    symptoms: list[str] = Field(min_length=1, max_length=30)
    age_group: str | None = Field(default=None, max_length=20)
    sex: str | None = Field(default=None, max_length=30)
    duration: str | None = Field(default=None, max_length=20)


@router.get("/symptoms")
def symptoms():
    """Return the full symptom checklist (ids, labels, groups)."""
    return {"symptoms": prediction.list_symptoms()}


@router.post("")
def predict(body: PredictRequest, user=Depends(get_current_user)):
    """Score the selected symptoms and return ranked possible conditions."""
    if body.age_group and body.age_group not in ALLOWED_AGE_GROUPS:
        raise HTTPException(status_code=422, detail="Invalid age group")
    if body.sex and body.sex not in ALLOWED_SEXES:
        raise HTTPException(status_code=422, detail="Invalid sex option")
    if body.duration and body.duration not in ALLOWED_DURATIONS:
        raise HTTPException(status_code=422, detail="Invalid duration option")

    result = prediction.run_prediction(
        symptom_ids=body.symptoms,
        age_group=body.age_group,
        sex=body.sex,
        duration=body.duration,
    )
    result["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Persist the run (symptom ids + full result) for history review.
    prediction_id = database.add_prediction(user["id"], body.symptoms, result)
    result["id"] = prediction_id

    return result


@router.get("/history")
def history(user=Depends(get_current_user)):
    """Return the user's past prediction runs, newest first."""
    return {"predictions": database.list_predictions(user["id"])}
