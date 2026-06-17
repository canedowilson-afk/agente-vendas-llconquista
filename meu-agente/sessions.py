"""
sessions.py — Gerencia PostgreSQL para Clínica LLConquista na VPS
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do Banco de Dados
DB_CONFIG = {
    "host": "shadeseekingbeardeddragon-postgres.cloudfy.live",
    "port": "8085",
    "database": "db",
    "user": "postgres",
    "password": "ASUMRROozQHhEXdgkjs6"
}

def get_connection():
    """Retorna uma conexão com o PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    """Cria tabelas no PostgreSQL se não existem."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de sessões
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            messages_json TEXT NOT NULL,
            last_activity BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de leads
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT UNIQUE,
            email TEXT,
            source TEXT,
            first_msg TEXT,
            sent_checkout INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de mensagens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            lead_id TEXT NOT NULL REFERENCES leads(id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts BIGINT NOT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Tabelas PostgreSQL verificadas/criadas.")

def load_session(session_id: str):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT messages_json, last_activity FROM sessions WHERE id = %s", (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or (time.time() - row["last_activity"]) > 1800:
        return None
    return json.loads(row["messages_json"])

def save_session(session_id: str, messages: list):
    conn = get_connection()
    cursor = conn.cursor()
    now = int(time.time())
    msg_json = json.dumps(messages)
    
    cursor.execute("""
        INSERT INTO sessions (id, messages_json, last_activity)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET 
            messages_json = EXCLUDED.messages_json, 
            last_activity = EXCLUDED.last_activity
    """, (session_id, msg_json, now))
    
    conn.commit()
    conn.close()

def create_lead(phone: str, name: str = None, email: str = None, source: str = "whatsapp"):
    conn = get_connection()
    cursor = conn.cursor()
    lead_id = f"{source}_{phone}"
    now = datetime.now()
    
    cursor.execute("""
        INSERT INTO leads (id, phone, name, email, source, first_msg, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET 
            name = COALESCE(EXCLUDED.name, leads.name), 
            updated_at = EXCLUDED.updated_at
        RETURNING id
    """, (lead_id, phone, name, email, source, "", now, now))
    
    conn.commit()
    conn.close()
    return lead_id

def add_message(lead_id: str, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (lead_id, role, content, ts) VALUES (%s, %s, %s, %s)",
        (lead_id, role, content, int(time.time()))
    )
    conn.commit()
    conn.close()

def mark_checkout_sent(lead_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leads SET sent_checkout = 1, updated_at = %s WHERE id = %s",
        (datetime.now(), lead_id)
    )
    conn.commit()
    conn.close()
