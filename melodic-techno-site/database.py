"""
database.py — SQLite (local dev) or PostgreSQL (production via DATABASE_URL).
All tables are created automatically on first run.
"""

import os
import secrets

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ── Connection helpers ────────────────────────────────────────────────────────

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    def get_connection():
        return psycopg2.connect(DATABASE_URL)

    def _exec(conn, sql, params=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            try:
                return cur.fetchall()
            except psycopg2.ProgrammingError:
                return []

    def _exec_one(conn, sql, params=()):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    P = "%s"  # PostgreSQL placeholder

    def init_db():
        with get_connection() as conn:
            _exec(conn, """
                CREATE TABLE IF NOT EXISTS subscribers (
                    id         SERIAL PRIMARY KEY,
                    email      TEXT NOT NULL UNIQUE,
                    token      TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            _exec(conn, """
                CREATE TABLE IF NOT EXISTS email_logs (
                    id              SERIAL PRIMARY KEY,
                    subject         TEXT NOT NULL,
                    body            TEXT NOT NULL,
                    recipient_count INTEGER NOT NULL DEFAULT 0,
                    sent_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

else:
    import sqlite3

    DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "site.db")

    def get_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _exec(conn, sql, params=()):
        return conn.execute(sql, params).fetchall()

    def _exec_one(conn, sql, params=()):
        return conn.execute(sql, params).fetchone()

    P = "?"  # SQLite placeholder

    def init_db():
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    email      TEXT NOT NULL UNIQUE,
                    token      TEXT NOT NULL,
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
    with get_connection() as conn:
        row = _exec_one(conn, f"SELECT token FROM subscribers WHERE email = {P}", (email,))
        if row:
            return row["token"]
        token = secrets.token_urlsafe(32)
        _exec(conn, f"INSERT INTO subscribers (email, token) VALUES ({P}, {P})", (email, token))
        if DATABASE_URL:
            conn.commit()
        return token


def get_subscriber_by_token(token: str):
    with get_connection() as conn:
        return _exec_one(conn, f"SELECT * FROM subscribers WHERE token = {P}", (token,))


def get_all_subscribers():
    with get_connection() as conn:
        return _exec(conn, "SELECT id, email, created_at FROM subscribers ORDER BY created_at DESC")


def get_subscriber_emails() -> list[str]:
    with get_connection() as conn:
        rows = _exec(conn, "SELECT email FROM subscribers")
        return [r["email"] for r in rows]


def get_subscriber_emails_by_ids(ids: list[int]) -> list[str]:
    placeholders = ",".join([P] * len(ids))
    with get_connection() as conn:
        rows = _exec(conn, f"SELECT email FROM subscribers WHERE id IN ({placeholders})", ids)
        return [r["email"] for r in rows]


def delete_subscriber(subscriber_id: int):
    with get_connection() as conn:
        _exec(conn, f"DELETE FROM subscribers WHERE id = {P}", (subscriber_id,))
        if DATABASE_URL:
            conn.commit()


def subscriber_count() -> int:
    with get_connection() as conn:
        row = _exec_one(conn, "SELECT COUNT(*) AS c FROM subscribers")
        return row["c"]


# ── Email log helpers ─────────────────────────────────────────────────────────

def log_email_send(subject: str, body: str, recipient_count: int):
    with get_connection() as conn:
        _exec(conn,
              f"INSERT INTO email_logs (subject, body, recipient_count) VALUES ({P}, {P}, {P})",
              (subject, body, recipient_count))
        if DATABASE_URL:
            conn.commit()


def get_email_logs():
    with get_connection() as conn:
        return _exec(conn, "SELECT * FROM email_logs ORDER BY sent_at DESC")
