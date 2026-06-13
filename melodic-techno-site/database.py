"""
database.py — SQLite setup and query helpers.
All tables are created automatically on first run.
"""

import sqlite3
import os
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "site.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def init_db():
    """Create tables if they don't exist yet."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                email     TEXT    NOT NULL UNIQUE,
                token     TEXT    NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS email_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                subject         TEXT NOT NULL,
                body            TEXT NOT NULL,
                recipient_count INTEGER NOT NULL DEFAULT 0,
                sent_at         DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)


# ── Subscriber helpers ────────────────────────────────────────────────────────

def add_subscriber(email: str) -> str:
    """
    Insert a new subscriber and return their access token.
    If the email already exists, return the existing token.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT token FROM subscribers WHERE email = ?", (email,)
        ).fetchone()
        if row:
            return row["token"]
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO subscribers (email, token) VALUES (?, ?)",
            (email, token),
        )
        return token


def get_subscriber_by_token(token: str):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM subscribers WHERE token = ?", (token,)
        ).fetchone()


def get_all_subscribers():
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, email, created_at FROM subscribers ORDER BY created_at DESC"
        ).fetchall()


def get_subscriber_emails() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT email FROM subscribers").fetchall()
        return [r["email"] for r in rows]


def get_subscriber_emails_by_ids(ids: list[int]) -> list[str]:
    placeholders = ",".join("?" * len(ids))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT email FROM subscribers WHERE id IN ({placeholders})", ids
        ).fetchall()
        return [r["email"] for r in rows]


def delete_subscriber(subscriber_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM subscribers WHERE id = ?", (subscriber_id,))


def subscriber_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]


# ── Email log helpers ─────────────────────────────────────────────────────────

def log_email_send(subject: str, body: str, recipient_count: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO email_logs (subject, body, recipient_count) VALUES (?, ?, ?)",
            (subject, body, recipient_count),
        )


def get_email_logs():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM email_logs ORDER BY sent_at DESC"
        ).fetchall()
