"""
database.py
SQLite database layer for the AI Healthcare Assistant.

Stores:
  - users          : authentication accounts (username, password hash, admin flag)
  - chat_history   : every question/answer pair per user
  - documents      : metadata about uploaded / auto-indexed medical documents

All functions use a lock because sqlite3 connections are not thread-safe by
default and FastAPI serves requests from a thread pool.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime

# Resolve the SQLite file from DATABASE_URL (e.g. sqlite:///./chatbot.db)
_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")
DB_PATH = _DB_URL.replace("sqlite:///", "")

_lock = threading.Lock()


def _now() -> str:
    """Return the current UTC timestamp as an ISO string."""
    return datetime.utcnow().isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    """Return a new connection whose rows can be accessed by column name."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they do not exist. Called once on startup."""
    with _lock:
        conn = get_connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_admin      INTEGER NOT NULL DEFAULT 0,
                    created_at    TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_history (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    role       TEXT NOT NULL,  -- 'user' or 'assistant'
                    message    TEXT NOT NULL,
                    sources    TEXT NOT NULL DEFAULT '[]',  -- JSON list of source files
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename     TEXT NOT NULL,
                    uploader     TEXT NOT NULL,
                    chunk_count  INTEGER NOT NULL DEFAULT 0,
                    uploaded_at  TEXT NOT NULL
                );
                """
            )
            conn.commit()

            # Migrate existing databases that predate the sources column.
            try:
                conn.execute(
                    "ALTER TABLE chat_history ADD COLUMN sources TEXT NOT NULL DEFAULT '[]'"
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()


# ------------------------------------------------------------------ users
def create_user(username: str, password_hash: str, is_admin: bool = False) -> int:
    """Insert a new user and return the new user id."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, int(is_admin), _now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def get_user_by_username(username: str) -> dict | None:
    """Fetch a user by username."""
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by id."""
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


# ------------------------------------------------------------------ chat history
def add_chat_message(
    user_id: int, role: str, message: str, sources: list | None = None
) -> None:
    """Store a single chat message for a user.

    ``sources`` is an optional list of document filenames the assistant's
    answer was drawn from; it is stored as JSON so citations survive reloads.
    """
    payload = json.dumps(sources or [])
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO chat_history (user_id, role, message, sources, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, role, message, payload, _now()),
            )
            conn.commit()
        finally:
            conn.close()


def get_chat_history(user_id: int, limit: int = 200) -> list[dict]:
    """Return the most recent messages for a user, oldest first."""
    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, role, message, sources, created_at FROM chat_history "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            # rows are newest-first, so reverse them for chronological display
            result = []
            for r in reversed(rows):
                row = dict(r)
                try:
                    row["sources"] = json.loads(row.get("sources") or "[]")
                except (ValueError, TypeError):
                    row["sources"] = []
                result.append(row)
            return result
        finally:
            conn.close()


def clear_chat_history(user_id: int) -> None:
    """Delete every message belonging to a user."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()


# ------------------------------------------------------------------ documents
def add_document(filename: str, uploader: str, chunk_count: int) -> int:
    """Register a document in the documents table."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO documents (filename, uploader, chunk_count, uploaded_at) VALUES (?, ?, ?, ?)",
                (filename, uploader, chunk_count, _now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def list_documents() -> list[dict]:
    """List all indexed documents, newest first."""
    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def delete_document(doc_id: int) -> None:
    """Remove a document record from the database."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
        finally:
            conn.close()
