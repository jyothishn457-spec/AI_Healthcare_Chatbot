"""
main.py
FastAPI entry point for the HealthPilot AI backend.

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000

The app is assembled from feature routers (see routers/):

    auth, chat, appointments, records, profile, prediction, documents

Legacy endpoints (/history) are kept for backward compatibility.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE importing modules that read environment variables.
load_dotenv()

import database
from auth import hash_password
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import appointments, auth, chat, documents, prediction, profile, records

DATA_DIR = Path(os.getenv("DATA_DIR", "../data/medical_documents"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


# ------------------------------------------------------------------ lifespan
def _ensure_default_admin() -> None:
    """Create the default admin account on first run."""
    admin_user = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    if not database.get_user_by_username(admin_user):
        database.create_user(admin_user, hash_password(admin_pass), is_admin=True)


def _index_new_documents() -> None:
    """Automatically index any new files found in the data folder on startup."""
    from rag_pipeline import index_document

    indexed = {doc["filename"] for doc in database.list_documents()}
    for file in sorted(DATA_DIR.iterdir()):
        if (
            file.is_file()
            and file.suffix.lower() in ALLOWED_EXTENSIONS
            and file.name not in indexed
        ):
            try:
                chunks = index_document(str(file))
                database.add_document(file.name, "system", chunks)
                print(f"[startup] Indexed {file.name} ({chunks} chunks)")
            except Exception as exc:  # pragma: no cover
                print(f"[startup] Could not index {file.name}: {exc}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Any startup problem (DB init, missing API key, vector store) must never
    # prevent the server from booting - log it and continue serving requests.
    try:
        database.init_db()
        _ensure_default_admin()
        _index_new_documents()
    except Exception as exc:  # pragma: no cover
        print(f"[startup] Non-fatal startup issue: {exc}")
    yield


app = FastAPI(
    title="HealthPilot AI API",
    description=(
        "AI-powered medical assistant backend: RAG chatbot, symptom prediction, "
        "appointments, medical records and user profiles."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# The client authenticates with a Bearer token in the Authorization header,
# so credentials are not needed and a permissive CORS policy is acceptable
# for development. Tighten the origins list before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ base endpoints
@app.get("/", tags=["meta"])
def root():
    return {"app": "HealthPilot AI API", "status": "running", "version": "2.0.0"}


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# Legacy history endpoints kept for older clients.
@app.get("/history", tags=["chat"])
def history(user=Depends(auth.get_current_user)):
    """Return the ungrouped chat history for the current user."""
    return database.get_chat_history(user["id"], session_id=None)


@app.delete("/history", tags=["chat"])
def clear_history(user=Depends(auth.get_current_user)):
    """Delete all chat history for the current user."""
    database.clear_chat_history(user["id"])
    return {"status": "cleared"}


# ------------------------------------------------------------------ routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(appointments.router)
app.include_router(records.router)
app.include_router(profile.router)
app.include_router(prediction.router)
app.include_router(documents.router)
