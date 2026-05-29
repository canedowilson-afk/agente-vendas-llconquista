"""
sessions.py — Gerencia SQLite de sessões e conversas
"""

import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime

DB_PATH = Path("dados.sqlite")


def _db():
    db_file = DB_PATH
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            messages_json TEXT NOT NULL,
            last_activity INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT UNIQUE,
            email TEXT,
            source TEXT,
            first_msg TEXT,
            sent_checkout INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts INTEGER NOT NULL,
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        )
    """)
    conn.commit()
    conn.close()


def load_session(session_id: str):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute("SELECT messages_json, last_activity FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    if time.time() - row["last_activity"] > 1800:
        return None
    return json.loads(row["messages_json"])


def save_session(session_id: str, messages: list):
    conn = _db()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute(
        """
        INSERT INTO sessions (id, messages_json, last_activity, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            messages_json = ?,
            last_activity = ?
        """,
        (session_id, json.dumps(messages), now, datetime.now().isoformat(), json.dumps(messages), now)
    )
    conn.commit()
    conn.close()


def create_lead(phone: str, name: str = None, email: str = None, source: str = "whatsapp"):
    conn = _db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    lead_id = f"{source}_{phone}"
    cursor.execute(
        """
        INSERT INTO leads (id, phone, name, email, source, first_msg, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = COALESCE(?, name),
            email = COALESCE(?, email),
            updated_at = ?
        """,
        (lead_id, phone, name, email, source, "", now, now, name, email, now)
    )
    conn.commit()
    conn.close()
    return lead_id


def add_message(lead_id: str, role: str, content: str):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (lead_id, role, content, ts) VALUES (?, ?, ?, ?)",
        (lead_id, role, content, int(time.time()))
    )
    conn.commit()
    conn.close()


def mark_checkout_sent(lead_id: str):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leads SET sent_checkout = 1, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), lead_id)
    )
    conn.commit()
    conn.close()
