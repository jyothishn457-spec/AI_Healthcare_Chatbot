"""
routers/chat.py
AI Doctor chat endpoints: ask questions, manage conversations.

Supports grouping messages into named sessions so a user can start a new
conversation or continue an old one. The answer is always produced by the
RAG pipeline with an embedded medical disclaimer (see chatbot.SYSTEM_PROMPT).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import database
from auth import get_current_user
from chatbot import generate_answer
from ratelimit import rate_limit

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


def _session_title(message: str) -> str:
    """Derive a readable conversation title from its first message."""
    title = " ".join(message.split())
    return title[:60] + ("..." if len(title) > 60 else "")


def _require_owned_session(session_id: int, user_id: int) -> dict:
    """Return a session or 404 if it does not belong to the user."""
    session = database.get_chat_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return session


@router.post("")
def chat(body: ChatRequest, request: Request, user=Depends(get_current_user)):
    """Answer a question, creating or continuing a conversation."""
    rate_limit(request)
    session_id = body.session_id

    if session_id is not None:
        # Continue an existing conversation.
        _require_owned_session(session_id, user["id"])
    else:
        # Start a new conversation.
        session_id = database.create_chat_session(user["id"], _session_title(body.message))

    try:
        response, sources = generate_answer(
            body.message.strip(), user_id=user["id"], session_id=session_id
        )
    except RuntimeError as exc:
        # Raised when an API key is missing / misconfigured.
        raise HTTPException(
            status_code=500, detail=f"Chatbot configuration error: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate answer: {exc}"
        ) from exc

    # Keep the session title useful: if it is still generic, use the message.
    session = database.get_chat_session(session_id, user["id"])
    if session and session["title"] in ("New conversation", ""):
        database.update_chat_session_title(session_id, user["id"], _session_title(body.message))
    database.touch_chat_session(session_id, user["id"])

    return {
        "response": response,
        "sources": sources,
        "session_id": session_id,
        "session_title": _session_title(body.message),
    }


@router.post("/sessions")
def create_session(user=Depends(get_current_user)):
    """Create a new empty conversation."""
    session_id = database.create_chat_session(user["id"])
    session = database.get_chat_session(session_id, user["id"])
    return {"session": session}


@router.get("/sessions")
def list_sessions(user=Depends(get_current_user)):
    """List the user's conversations, most recent first."""
    return {"sessions": database.list_chat_sessions(user["id"])}


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user=Depends(get_current_user)):
    """Return one conversation with its full message history."""
    session = _require_owned_session(session_id, user["id"])
    messages = database.get_chat_history(user["id"], session_id=session_id)
    return {"session": session, "messages": messages}


@router.patch("/sessions/{session_id}")
def rename_session(
    session_id: int, body: RenameRequest, user=Depends(get_current_user)
):
    """Rename a conversation."""
    _require_owned_session(session_id, user["id"])
    database.update_chat_session_title(session_id, user["id"], body.title.strip())
    return {"status": "renamed", "title": body.title.strip()}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user=Depends(get_current_user)):
    """Delete a conversation and its messages."""
    _require_owned_session(session_id, user["id"])
    database.delete_chat_session(session_id, user["id"])
    return {"status": "deleted"}
