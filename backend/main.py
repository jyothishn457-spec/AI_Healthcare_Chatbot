"""
main.py
FastAPI entry point for the AI Healthcare Assistant backend.

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000

Endpoints:
    POST  /register            create an account
    POST  /login               authenticate and get a JWT
    POST  /chat                ask the chatbot a question
    GET   /history             chat history for the current user
    DELETE /history            clear chat history
    POST  /upload              (admin) upload & index a medical document
    GET   /documents           (admin) list indexed documents
    DELETE /documents/{id}     (admin) delete a document
"""

import os
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE importing modules that read environment variables.
load_dotenv()

import database
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from chatbot import generate_answer
from rag_pipeline import index_document
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ------------------------------------------------------------------ settings
DATA_DIR = Path(os.getenv("DATA_DIR", "../data/medical_documents"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))   # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))         # requests / window / IP
MAX_UPLOAD_BYTES = 20 * 1024 * 1024                             # 20 MB
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
    title="AI Healthcare Assistant API",
    description="RAG-powered healthcare chatbot backend",
    version="1.0.0",
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


# ------------------------------------------------------------------ rate limit
_requests: dict[str, list[float]] = {}


def rate_limit(ip: str) -> None:
    """Simple in-memory sliding-window rate limiter per IP address."""
    now = time.time()
    window = [t for t in _requests.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
    if len(window) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    window.append(now)
    _requests[ip] = window

    # Prune stale entries so the map does not grow forever.
    if len(_requests) > 5000:
        _requests.clear()


# ------------------------------------------------------------------ request models
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


# ------------------------------------------------------------------ basic endpoints
@app.get("/")
def root():
    return {"app": "AI Healthcare Assistant API", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------------------------ auth endpoints
@app.post("/register")
def register(body: RegisterRequest):
    """Create a new user account and return a token (auto-login)."""
    username = body.username.strip()
    if database.get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username already taken")

    user_id = database.create_user(username, hash_password(body.password), is_admin=False)
    token = create_access_token(user_id, username, False)
    return {"token": token, "user": {"id": user_id, "username": username, "is_admin": False}}


@app.post("/login")
def login(body: LoginRequest, request: Request):
    """Authenticate a user and return a JWT token."""
    rate_limit(request.client.host)
    user = database.get_user_by_username(body.username.strip())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user["id"], user["username"], bool(user["is_admin"]))
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "is_admin": bool(user["is_admin"]),
        },
    }


# ------------------------------------------------------------------ chat endpoints
@app.post("/chat")
def chat(body: ChatRequest, request: Request, user=Depends(get_current_user)):
    """Answer a user question using the RAG pipeline."""
    rate_limit(request.client.host)
    try:
        response = generate_answer(body.message.strip(), user_id=user["id"])
        return {"response": response}
    except RuntimeError as exc:
        # Raised when an API key is missing / misconfigured.
        raise HTTPException(
            status_code=500, detail=f"Chatbot configuration error: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate answer: {exc}"
        ) from exc


@app.get("/history")
def history(user=Depends(get_current_user)):
    """Return the chat history for the current user."""
    return database.get_chat_history(user["id"])


@app.delete("/history")
def clear_history(user=Depends(get_current_user)):
    """Delete all chat history for the current user."""
    database.clear_chat_history(user["id"])
    return {"status": "cleared"}


# ------------------------------------------------------------------ document endpoints (admin)
@app.post("/upload")
def upload(file: UploadFile = File(...), user=Depends(require_admin)):
    """(Admin) Upload and index a medical document (PDF / TXT / DOCX)."""
    filename = file.filename or "document"
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Only .pdf, .txt and .docx files are allowed"
        )

    # Save to disk while enforcing a size limit.
    dest = DATA_DIR / Path(filename).name
    size = 0
    try:
        with dest.open("wb") as buffer:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413, detail="File too large (max 20 MB)"
                    )
                buffer.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise

    # Embed the document into the vector store.
    try:
        chunks = index_document(str(dest))
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400, detail=f"Failed to index document: {exc}"
        ) from exc

    doc_id = database.add_document(dest.name, user["username"], chunks)
    return {"id": doc_id, "filename": dest.name, "chunks": chunks, "status": "indexed"}


@app.get("/documents")
def documents(user=Depends(require_admin)):
    """(Admin) List all indexed documents."""
    return database.list_documents()


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int, user=Depends(require_admin)):
    """(Admin) Delete a document from disk, the vector store and the database."""
    docs = database.list_documents()
    target = next((d for d in docs if d["id"] == doc_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Document not found")

    # 1. Remove the file from disk.
    (DATA_DIR / target["filename"]).unlink(missing_ok=True)

    # 2. Remove its chunks from ChromaDB.
    from rag_pipeline import get_collection

    try:
        collection = get_collection()
        ids = collection.get(where={"source": target["filename"]})["ids"]
        if ids:
            collection.delete(ids=ids)
    except Exception:
        pass

    # 3. Remove the database record.
    database.delete_document(doc_id)

    return {"status": "deleted", "filename": target["filename"]}
