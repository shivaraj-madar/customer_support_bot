"""
tickets.py — SQLite ticket storage for escalated conversations
Tables: tickets, messages
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "tickets.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id   TEXT    UNIQUE NOT NULL,
                user_id     TEXT,
                user_name   TEXT,
                user_email  TEXT,
                user_plan   TEXT,
                status      TEXT    DEFAULT 'open',
                reason      TEXT,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id   TEXT    NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
            );
        """)


def create_ticket(ticket_id: str, user_id: str, user_info: dict,
                  conversation: list, reason: str = "") -> dict:
    """Save a new escalation ticket with full conversation."""
    now = datetime.now().isoformat(sep=" ", timespec="seconds")

    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO tickets
                (ticket_id, user_id, user_name, user_email, user_plan,
                 status, reason, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)
        """, (
            ticket_id,
            user_id or "guest",
            user_info.get("name", "Unknown"),
            user_info.get("email", ""),
            user_info.get("plan", ""),
            reason,
            now, now
        ))

        for msg in conversation:
            role    = "user" if msg.__class__.__name__ == "HumanMessage" else "bot"
            content = msg.content
            conn.execute("""
                INSERT INTO messages (ticket_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (ticket_id, role, content, now))

    return get_ticket(ticket_id)


def get_ticket(ticket_id: str) -> dict:
    """Get a single ticket with its messages."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if not row:
            return None
        ticket = dict(row)
        msgs   = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE ticket_id = ? ORDER BY id",
            (ticket_id,)
        ).fetchall()
        ticket["messages"] = [dict(m) for m in msgs]
        return ticket


def get_all_tickets(status: str = None) -> list:
    """Get all tickets, optionally filtered by status."""
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tickets ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_status(ticket_id: str, status: str) -> bool:
    """Update ticket status: open → in_progress → closed."""
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
            (status, now, ticket_id)
        )
        return cur.rowcount > 0


def get_stats() -> dict:
    """Return summary counts for dashboard."""
    with get_conn() as conn:
        total       = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        open_count  = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
        inprog      = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'").fetchone()[0]
        closed      = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='closed'").fetchone()[0]
        today       = datetime.now().strftime("%Y-%m-%d")
        today_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE created_at LIKE ?", (today + "%",)
        ).fetchone()[0]
    return {
        "total": total, "open": open_count,
        "in_progress": inprog, "closed": closed, "today": today_count
    }


# Auto-init on import
init_db()