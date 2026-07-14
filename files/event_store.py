"""
event_store.py
Stores file monitoring events (created/deleted/modified) permanently
in a local SQLite database, so history survives app restarts.
"""
import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.expanduser("~"), ".file_monitor_history.db")


def _get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            email_sent INTEGER DEFAULT 0
        )
        """
    )
    return conn


def add_event(event_type: str, file_path: str, email_sent: int = 0) -> int:
    """Insert a new event record and return its row ID."""
    conn = _get_conn()
    cursor = conn.cursor()
    with conn:
        cursor.execute(
            "INSERT INTO events (timestamp, event_type, file_path, email_sent) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), event_type, file_path, email_sent),
        )
        row_id = cursor.lastrowid
    conn.close()
    return row_id


def update_email_status(row_ids: list, email_sent: int):
    """Update email_sent status for a list of event row IDs."""
    if not row_ids:
        return
    conn = _get_conn()
    with conn:
        placeholders = ",".join("?" for _ in row_ids)
        conn.execute(
            f"UPDATE events SET email_sent = ? WHERE id IN ({placeholders})",
            [email_sent] + list(row_ids)
        )
    conn.close()


def update_event_path(row_id: int, new_path: str):
    """Update file_path for a specific event ID (e.g. during renames)."""
    conn = _get_conn()
    with conn:
        conn.execute("UPDATE events SET file_path = ? WHERE id = ?", (new_path, row_id))
    conn.close()


def get_recent_events(limit: int = 200):
    """Return the most recent events, newest first."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT timestamp, event_type, file_path, email_sent FROM events "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def clear_history():
    """Wipe all stored events."""
    conn = _get_conn()
    with conn:
        conn.execute("DELETE FROM events")
    conn.close()
