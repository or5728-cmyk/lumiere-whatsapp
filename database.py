import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE_PATH


def _conn() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                id_message TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_followups (
                chat_id TEXT PRIMARY KEY,
                sender_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def append(chat_id: str, role: str, content: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO conversations (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, datetime.utcnow().isoformat())
        )
        conn.commit()


def tail(chat_id: str, n: int = 20) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM (
                SELECT role, content, created_at
                FROM conversations
                WHERE chat_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) ORDER BY created_at ASC
            """,
            (chat_id, n)
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def add_pending_followup(chat_id: str, sender_name: str) -> None:
    """Save a customer who wrote outside hours — needs a follow-up at next opening."""
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO pending_followups (chat_id, sender_name, created_at) VALUES (?, ?, ?)",
            (chat_id, sender_name, datetime.utcnow().isoformat())
        )
        conn.commit()


def get_pending_followups() -> list[dict]:
    """Return all customers waiting for a follow-up."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT chat_id, sender_name FROM pending_followups"
        ).fetchall()
    return [{"chat_id": row["chat_id"], "sender_name": row["sender_name"]} for row in rows]


def remove_pending_followup(chat_id: str) -> None:
    """Remove a pending follow-up — either sent or cancelled (customer wrote again)."""
    with _conn() as conn:
        conn.execute("DELETE FROM pending_followups WHERE chat_id = ?", (chat_id,))
        conn.commit()


def clear_history(chat_id: str) -> None:
    """Delete all conversation history for a given chat_id."""
    with _conn() as conn:
        conn.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
        conn.commit()


def is_processed(id_message: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_messages WHERE id_message = ?",
            (id_message,)
        ).fetchone()
    return row is not None


def mark_processed(id_message: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_messages (id_message, processed_at) VALUES (?, ?)",
            (id_message, datetime.utcnow().isoformat())
        )
        conn.commit()
