"""
routers/documents.py
Admin document management: upload, list and delete medical documents that
feed the RAG knowledge base.
"""

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

import database
from auth import require_admin
from rag_pipeline import get_collection, index_document

router = APIRouter(tags=["documents"])

# Upload settings (mirrored from the previous single-file layout).
DATA_DIR = Path(os.getenv("DATA_DIR", "../data/medical_documents"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024                             # 20 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


@router.post("/upload")
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


@router.get("/documents")
def documents(user=Depends(require_admin)):
    """(Admin) List all indexed documents."""
    return database.list_documents()


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, user=Depends(require_admin)):
    """(Admin) Delete a document from disk, the vector store and the database."""
    docs = database.list_documents()
    target = next((d for d in docs if d["id"] == doc_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Document not found")

    # 1. Remove the file from disk.
    (DATA_DIR / target["filename"]).unlink(missing_ok=True)

    # 2. Remove its chunks from ChromaDB.
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
