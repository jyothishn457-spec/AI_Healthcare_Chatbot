"""
database.py
SQLite database layer for the AI Healthcare Assistant (HealthPilot AI).

Stores:
  - users           : accounts (username, password hash, admin flag, profile fields)
  - refresh_tokens  : revocable refresh tokens for session refresh
  - chat_sessions   : named chat conversations per user
  - chat_history    : every question/answer pair per user (optional session group)
  - appointments    : booked / requested doctor appointments
  - medical_history : past medical events (timeline)
  - prescriptions   : medication records
  - predictions     : symptom -> condition prediction history
  - documents       : metadata about uploaded / auto-indexed medical documents

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

# Default JSON notification preferences for new users.
DEFAULT_NOTIFICATION_PREFS = {
    "appointment_reminders": True,
    "prescription_updates": True,
    "health_tips": False,
    "email_summary": False,
}


def _now() -> str:
    """Return the current UTC timestamp as an ISO string."""
    return datetime.utcnow().isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    """Return a new connection whose rows can be accessed by column name."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return True when ``column`` exists on ``table`` (used for migrations)."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def init_db() -> None:
    """Create all tables (and migrate old ones) if they do not exist."""
    with _lock:
        conn = get_connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    username           TEXT NOT NULL UNIQUE,
                    password_hash      TEXT NOT NULL,
                    is_admin           INTEGER NOT NULL DEFAULT 0,
                    created_at         TEXT NOT NULL,
                    full_name          TEXT NOT NULL DEFAULT '',
                    email              TEXT NOT NULL DEFAULT '',
                    phone              TEXT NOT NULL DEFAULT '',
                    date_of_birth      TEXT NOT NULL DEFAULT '',
                    gender             TEXT NOT NULL DEFAULT 'prefer not to say',
                    notification_prefs TEXT NOT NULL DEFAULT '{}',
                    avatar_color       TEXT NOT NULL DEFAULT '#0e7c86'
                );

                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    title      TEXT NOT NULL DEFAULT 'New conversation',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chat_history (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    session_id INTEGER,
                    role       TEXT NOT NULL,  -- 'user' or 'assistant'
                    message    TEXT NOT NULL,
                    sources    TEXT NOT NULL DEFAULT '[]',  -- JSON list of source files
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS appointments (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER NOT NULL,
                    doctor_name  TEXT NOT NULL,
                    specialty    TEXT NOT NULL,
                    date         TEXT NOT NULL,  -- YYYY-MM-DD
                    time         TEXT NOT NULL,  -- HH:MM
                    notes        TEXT NOT NULL DEFAULT '',
                    status       TEXT NOT NULL DEFAULT 'pending',
                    created_at   TEXT NOT NULL,
                    updated_at   TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS medical_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    title       TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    event_date  TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS prescriptions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER NOT NULL,
                    medication   TEXT NOT NULL,
                    dosage       TEXT NOT NULL DEFAULT '',
                    frequency    TEXT NOT NULL DEFAULT '',
                    prescriber   TEXT NOT NULL DEFAULT '',
                    start_date   TEXT NOT NULL,
                    notes        TEXT NOT NULL DEFAULT '',
                    active       INTEGER NOT NULL DEFAULT 1,
                    created_at   TEXT NOT NULL,
                    updated_at   TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS predictions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    symptoms   TEXT NOT NULL DEFAULT '[]',  -- JSON list of symptom ids
                    result     TEXT NOT NULL,               -- JSON result payload
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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

            # ---- Migrations for databases created before these columns/tables ----
            # 1. Profile columns on users.
            for column, ddl in (
                ("full_name", "TEXT NOT NULL DEFAULT ''"),
                ("email", "TEXT NOT NULL DEFAULT ''"),
                ("phone", "TEXT NOT NULL DEFAULT ''"),
                ("date_of_birth", "TEXT NOT NULL DEFAULT ''"),
                ("gender", "TEXT NOT NULL DEFAULT 'prefer not to say'"),
                ("notification_prefs", "TEXT NOT NULL DEFAULT '{}'"),
                ("avatar_color", "TEXT NOT NULL DEFAULT '#0e7c86'"),
            ):
                if not _column_exists(conn, "users", column):
                    conn.execute(f"ALTER TABLE users ADD COLUMN {column} {ddl}")

            # 2. Sources column on chat_history (pre-existing migration).
            if not _column_exists(conn, "chat_history", "sources"):
                conn.execute(
                    "ALTER TABLE chat_history ADD COLUMN sources TEXT NOT NULL DEFAULT '[]'"
                )

            # 3. session_id grouping on chat_history.
            if not _column_exists(conn, "chat_history", "session_id"):
                conn.execute(
                    "ALTER TABLE chat_history ADD COLUMN session_id INTEGER"
                )
            conn.commit()

            # 4. Seed default notification prefs for existing users that have none.
            conn.execute(
                "UPDATE users SET notification_prefs = ? WHERE notification_prefs = '{}'",
                (json.dumps(DEFAULT_NOTIFICATION_PREFS),),
            )
            conn.commit()
        finally:
            conn.close()


# ================================================================== users
def create_user(username: str, password_hash: str, is_admin: bool = False) -> int:
    """Insert a new user and return the new user id."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, is_admin, created_at, notification_prefs) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, int(is_admin), _now(),
                 json.dumps(DEFAULT_NOTIFICATION_PREFS)),
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
            return _normalize_user(row)
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
            return _normalize_user(row)
        finally:
            conn.close()


def _normalize_user(row: sqlite3.Row | None) -> dict | None:
    """Convert a user row to a dict, parsing the JSON preferences column."""
    if not row:
        return None
    user = dict(row)
    try:
        user["notification_prefs"] = json.loads(user.get("notification_prefs") or "{}")
    except (ValueError, TypeError):
        user["notification_prefs"] = dict(DEFAULT_NOTIFICATION_PREFS)
    return user


def update_user_profile(user_id: int, fields: dict) -> None:
    """Update the profile columns of a user.

    ``fields`` maps column names to values (already validated by the API layer).
    """
    allowed = {
        "full_name", "email", "phone", "date_of_birth", "gender",
        "notification_prefs", "avatar_color",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    if "notification_prefs" in updates:
        updates["notification_prefs"] = json.dumps(updates["notification_prefs"])
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = [v for v in updates.values()] + [user_id]
    with _lock:
        conn = get_connection()
        try:
            conn.execute(f"UPDATE users SET {cols} WHERE id = ?", values)
            conn.commit()
        finally:
            conn.close()


def update_user_password(user_id: int, password_hash: str) -> None:
    """Replace a user's stored password hash."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )
            conn.commit()
        finally:
            conn.close()


def delete_user(user_id: int) -> None:
    """Permanently delete a user. Child rows are removed via ON DELETE CASCADE."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()


# ================================================================== refresh tokens
def store_refresh_token(user_id: int, token_hash: str, expires_at: str) -> int:
    """Persist a hashed refresh token so it can be revoked on logout."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, token_hash, expires_at, _now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def get_refresh_token(token_hash: str) -> dict | None:
    """Fetch a refresh-token record by its hash."""
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def delete_refresh_token(token_hash: str) -> None:
    """Revoke a single refresh token."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,))
            conn.commit()
        finally:
            conn.close()


def delete_all_refresh_tokens(user_id: int) -> None:
    """Revoke every refresh token for a user (used on logout / account deletion)."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()


# ================================================================== chat sessions
def create_chat_session(user_id: int, title: str = "New conversation") -> int:
    """Create a new chat session and return its id."""
    now = _now()
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO chat_sessions (user_id, title, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, title, now, now),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def list_chat_sessions(user_id: int) -> list[dict]:
    """List a user's sessions with message counts, most recent first."""
    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT s.id, s.title, s.created_at, s.updated_at, "
                "       (SELECT COUNT(*) FROM chat_history h "
                "         WHERE h.session_id = s.id) AS message_count "
                "FROM chat_sessions s WHERE s.user_id = ? "
                "ORDER BY s.updated_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_chat_session(session_id: int, user_id: int) -> dict | None:
    """Fetch a session, but only if it belongs to ``user_id``."""
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def update_chat_session_title(session_id: int, user_id: int, title: str) -> None:
    """Rename a user's session."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = ? "
                "WHERE id = ? AND user_id = ?",
                (title, _now(), session_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()


def touch_chat_session(session_id: int, user_id: int) -> None:
    """Bump the updated_at timestamp so the session sorts to the top."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                (_now(), session_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()


def delete_chat_session(session_id: int, user_id: int) -> None:
    """Delete a session and its messages (FK cascade)."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()


# ================================================================== chat history
def add_chat_message(
    user_id: int,
    role: str,
    message: str,
    sources: list | None = None,
    session_id: int | None = None,
) -> None:
    """Store a single chat message for a user.

    ``sources`` is an optional list of document filenames the assistant's
    answer was drawn from; it is stored as JSON so citations survive reloads.
    ``session_id`` groups the message into a conversation.
    """
    payload = json.dumps(sources or [])
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO chat_history (user_id, session_id, role, message, sources, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, session_id, role, message, payload, _now()),
            )
            conn.commit()
        finally:
            conn.close()


def get_chat_history(
    user_id: int, session_id: int | None = None, limit: int = 200
) -> list[dict]:
    """Return the most recent messages for a user/session, oldest first.

    When ``session_id`` is None, only messages without a session group
    (legacy "general" conversation) are returned.
    """
    with _lock:
        conn = get_connection()
        try:
            if session_id is not None:
                rows = conn.execute(
                    "SELECT id, session_id, role, message, sources, created_at "
                    "FROM chat_history WHERE user_id = ? AND session_id = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (user_id, session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, session_id, role, message, sources, created_at "
                    "FROM chat_history WHERE user_id = ? AND session_id IS NULL "
                    "ORDER BY id DESC LIMIT ?",
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


def clear_chat_history(user_id: int, session_id: int | None = None) -> None:
    """Delete every message belonging to a user (optionally one session)."""
    with _lock:
        conn = get_connection()
        try:
            if session_id is not None:
                conn.execute(
                    "DELETE FROM chat_history WHERE user_id = ? AND session_id = ?",
                    (user_id, session_id),
                )
            else:
                conn.execute(
                    "DELETE FROM chat_history WHERE user_id = ?", (user_id,)
                )
            conn.commit()
        finally:
            conn.close()


# ================================================================== appointments
def create_appointment(
    user_id: int, doctor_name: str, specialty: str, date: str, time: str, notes: str = ""
) -> int:
    """Create a new appointment with status 'pending'."""
    now = _now()
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO appointments (user_id, doctor_name, specialty, date, time, "
                "notes, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
                (user_id, doctor_name, specialty, date, time, notes, now, now),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def list_appointments(
    user_id: int, status: str | None = None, upcoming: bool = False
) -> list[dict]:
    """List a user's appointments.

    ``upcoming`` returns only today-or-later appointments, soonest first.
    Otherwise the list is newest-created first.
    """
    with _lock:
        conn = get_connection()
        try:
            if upcoming:
                sql = (
                    "SELECT * FROM appointments WHERE user_id = ? "
                    "AND status NOT IN ('cancelled', 'completed') "
                    "AND date >= date('now', 'localtime') "
                    "ORDER BY date ASC, time ASC"
                )
                rows = conn.execute(sql, (user_id,)).fetchall()
            else:
                sql = "SELECT * FROM appointments WHERE user_id = ?"
                args = [user_id]
                if status:
                    sql += " AND status = ?"
                    args.append(status)
                sql += " ORDER BY date DESC, time DESC"
                rows = conn.execute(sql, args).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_appointment(appointment_id: int, user_id: int) -> dict | None:
    """Fetch one appointment, scoped to the owner."""
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM appointments WHERE id = ? AND user_id = ?",
                (appointment_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def update_appointment(
    appointment_id: int, user_id: int, fields: dict
) -> bool:
    """Update mutable appointment fields; returns False when not found."""
    allowed = {"doctor_name", "specialty", "date", "time", "notes", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return True
    updates["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = [v for v in updates.values()] + [appointment_id, user_id]
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                f"UPDATE appointments SET {cols} WHERE id = ? AND user_id = ?",
                values,
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def delete_appointment(appointment_id: int, user_id: int) -> bool:
    """Delete an appointment owned by ``user_id``; returns False when not found."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "DELETE FROM appointments WHERE id = ? AND user_id = ?",
                (appointment_id, user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# ================================================================== medical history
def add_history_entry(user_id: int, title: str, description: str, event_date: str) -> int:
    """Add a medical-history timeline entry."""
    now = _now()
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO medical_history (user_id, title, description, event_date, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, title, description, event_date, now, now),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def list_history(user_id: int) -> list[dict]:
    """List medical history newest event first."""
    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM medical_history WHERE user_id = ? "
                "ORDER BY event_date DESC, id DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_history_entry(entry_id: int, user_id: int) -> dict | None:
    """Fetch one history entry, scoped to the owner."""
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM medical_history WHERE id = ? AND user_id = ?",
                (entry_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def update_history_entry(entry_id: int, user_id: int, fields: dict) -> bool:
    """Update a history entry; returns False when not found."""
    allowed = {"title", "description", "event_date"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return True
    updates["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = [v for v in updates.values()] + [entry_id, user_id]
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                f"UPDATE medical_history SET {cols} WHERE id = ? AND user_id = ?",
                values,
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def delete_history_entry(entry_id: int, user_id: int) -> bool:
    """Delete a history entry owned by ``user_id``."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "DELETE FROM medical_history WHERE id = ? AND user_id = ?",
                (entry_id, user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# ================================================================== prescriptions
def add_prescription(
    user_id: int,
    medication: str,
    dosage: str,
    frequency: str,
    prescriber: str,
    start_date: str,
    notes: str,
    active: bool = True,
) -> int:
    """Add a prescription record."""
    now = _now()
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO prescriptions (user_id, medication, dosage, frequency, "
                "prescriber, start_date, notes, active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, medication, dosage, frequency, prescriber, start_date,
                 notes, int(active), now, now),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def list_prescriptions(user_id: int, active_only: bool = False) -> list[dict]:
    """List prescriptions, active first then newest."""
    with _lock:
        conn = get_connection()
        try:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM prescriptions WHERE user_id = ? AND active = 1 "
                    "ORDER BY start_date DESC, id DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM prescriptions WHERE user_id = ? "
                    "ORDER BY active DESC, start_date DESC, id DESC",
                    (user_id,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_prescription(prescription_id: int, user_id: int) -> dict | None:
    """Fetch one prescription, scoped to the owner."""
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM prescriptions WHERE id = ? AND user_id = ?",
                (prescription_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def update_prescription(prescription_id: int, user_id: int, fields: dict) -> bool:
    """Update prescription fields; returns False when not found."""
    allowed = {
        "medication", "dosage", "frequency", "prescriber",
        "start_date", "notes", "active",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "active" in updates:
        updates["active"] = int(updates["active"])
    if not updates:
        return True
    updates["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = [v for v in updates.values()] + [prescription_id, user_id]
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                f"UPDATE prescriptions SET {cols} WHERE id = ? AND user_id = ?",
                values,
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def delete_prescription(prescription_id: int, user_id: int) -> bool:
    """Delete a prescription owned by ``user_id``."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "DELETE FROM prescriptions WHERE id = ? AND user_id = ?",
                (prescription_id, user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# ================================================================== predictions
def add_prediction(user_id: int, symptoms: list, result: dict) -> int:
    """Store a prediction run so users can review their history."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO predictions (user_id, symptoms, result, created_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, json.dumps(symptoms), json.dumps(result), _now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def list_predictions(user_id: int, limit: int = 20) -> list[dict]:
    """List prediction history, newest first."""
    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, symptoms, result, created_at FROM predictions "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            result = []
            for r in rows:
                row = dict(r)
                try:
                    row["symptoms"] = json.loads(row.get("symptoms") or "[]")
                    row["result"] = json.loads(row.get("result") or "{}")
                except (ValueError, TypeError):
                    pass
                result.append(row)
            return result
        finally:
            conn.close()


# ================================================================== documents
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
