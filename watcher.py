#!/usr/bin/env python3
"""
watcher.py — Monitora WhatsApp via Evolution API
"""

import sys
import io

# Forçar UTF-8 no stdout para evitar erros com emojis no Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import time
import logging
import os
import traceback
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env na pasta meu-agente
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("watcher.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from agent import handle_message

# Configuração
EVOLUTION_URL = os.getenv("EVOLUTION_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "meu-agente")
POLL_INTERVAL = 3

STATE_FILE = Path("watcher_state.json")

def evolution_request(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    url = f"{EVOLUTION_URL}{endpoint}"
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers=headers,
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            logger.error(f"Evolution API erro 401: Nao autorizado. Verifique a API Key no .env. URL: {url}")
        else:
            logger.error(f"Evolution API erro {e.code}: {e.reason}")
        return {}
    except Exception as e:
        logger.error(f"Evolution API erro: {e}")
        return {}

def fetch_messages(count: int = 20) -> list:
    result = evolution_request(
        f"/chat/findMessages/{INSTANCE_NAME}",
        method="POST",
        data={"count": count}
    )
    if isinstance(result, list): return result
    if isinstance(result, dict) and "messages" in result:
        messages_data = result["messages"]
        if isinstance(messages_data, dict): return messages_data.get("records", [])
        if isinstance(messages_data, list): return messages_data
    return []

def send_whatsapp(phone: str, message: str) -> bool:
    result = evolution_request(
        f"/message/sendText/{INSTANCE_NAME}",
        method="POST",
        data={"number": phone, "text": message}
    )
    success = bool(result.get("key") or result.get("id"))
    if success:
        logger.info(f"Enviado para {phone}")
    else:
        logger.error(f"Falha ao enviar para {phone}: {result}")
    return success

def extract_message_data(msg) -> dict:
    if not isinstance(msg, dict): return {}
    key = msg.get("key", {})
    if not isinstance(key, dict) or key.get("fromMe", False): return {}
    remote_jid = key.get("remoteJid", "")
    if "@g.us" in remote_jid: return {}
    
    if key.get("addressingMode") == "lid" and key.get("remoteJidAlt"):
        phone = key["remoteJidAlt"].replace("@s.whatsapp.net", "")
    else:
        phone = remote_jid.replace("@s.whatsapp.net", "").replace("@lid", "")
    
    push_name = msg.get("pushName", "Lead")
    message_content = msg.get("message", {})
    if not isinstance(message_content, dict): return {}
    
    text = (
        message_content.get("conversation") or
        (message_content.get("extendedTextMessage") or {}).get("text") or
        ""
    )
    return {"id": key.get("id", ""), "phone": phone, "name": push_name, "text": text.strip()}

def load_state() -> dict:
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"seen_ids": [], "last_run": None}

def save_state(state: dict):
    state["last_run"] = datetime.now().isoformat()
    if len(state["seen_ids"]) > 500: state["seen_ids"] = state["seen_ids"][-500:]
    STATE_FILE.write_text(json.dumps(state, indent=2))

def watch():
    logger.info("Watcher iniciado")
    state = load_state()
    from sessions import init_db
    init_db()

    while True:
        try:
            messages = fetch_messages(count=20)
            for msg in messages:
                msg_data = extract_message_data(msg)
                if not msg_data or not msg_data.get("phone") or not msg_data.get("text"): continue
                
                msg_id = msg_data["id"]
                if msg_id in state["seen_ids"]: continue
                
                state["seen_ids"].append(msg_id)
                phone = msg_data["phone"]
                name = msg_data["name"]
                text = msg_data["text"]
                
                logger.info(f"Mensagem de {name} ({phone}): {text[:60]}")
                try:
                    response = handle_message(phone, name, text)
                    if response:
                        send_whatsapp(phone, response)
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem: {e}")
            
            save_state(state)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Erro no loop: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    watch()
