import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / "meu-agente" / "dados.sqlite"
SESSION_TTL_SECONDS = 1800


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            messages_json TEXT NOT NULL,
            last_activity INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT UNIQUE,
            source TEXT,
            sent_checkout INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def load_session(session_id):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT messages_json, last_activity FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    if time.time() - row["last_activity"] > SESSION_TTL_SECONDS:
        return None
    return json.loads(row["messages_json"])


def save_session(session_id, messages):
    conn = _db()
    cursor = conn.cursor()
    now = int(time.time())
    created_at = datetime.now().isoformat()
    payload = json.dumps(messages, ensure_ascii=False)
    cursor.execute(
        """
        INSERT INTO sessions (id, messages_json, last_activity, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            messages_json = excluded.messages_json,
            last_activity = excluded.last_activity
        """,
        (session_id, payload, now, created_at),
    )
    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def create_lead(phone: str, name: str = None, source: str = "whatsapp"):
    conn = _db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    lead_id = f"{source}_{phone}"
    cursor.execute(
        """
        INSERT INTO leads (id, phone, name, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = COALESCE(excluded.name, leads.name),
            updated_at = excluded.updated_at
        """,
        (lead_id, phone, name, source, now, now),
    )
    conn.commit()
    conn.close()
    return lead_id


def add_message(lead_id, role, content):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (lead_id, role, content, ts) VALUES (?, ?, ?, ?)",
        (lead_id, role, content, int(time.time())),
    )
    conn.commit()
    conn.close()


def mark_checkout_sent(lead_id):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leads SET sent_checkout = 1, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), lead_id),
    )
    conn.commit()
    conn.close()


def has_checkout_sent(lead_id):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute("SELECT sent_checkout FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row["sent_checkout"])


def get_recent_messages(lead_id, limit=12):
    conn = _db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT role, content, ts
        FROM messages
        WHERE lead_id = ?
        ORDER BY ts DESC, id DESC
        LIMIT ?
        """,
        (lead_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    ordered = list(reversed(rows))
    return [{"role": row["role"], "content": row["content"]} for row in ordered]
