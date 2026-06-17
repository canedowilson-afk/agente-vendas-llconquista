"""
watcher.py — Monitora WhatsApp e ativa a Priscila da Clínica LLConquista
"""

import json
import time
import logging
import sys
import traceback
import urllib.request
import urllib.error
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

LOG_FILE = Path(__file__).parent / "watcher.log"
STATE_FILE = Path(__file__).parent / "watcher_state.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Importar agente Priscila
from agent import handle_message

EVOLUTION_URL = os.getenv("EVOLUTION_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
INSTANCE_NAME = os.getenv("INSTANCE_NAME")
POLL_INTERVAL = 3

def evolution_request(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    # Garantir que não haja barras duplicadas
    base_url = EVOLUTION_URL.rstrip('/')
    target_endpoint = endpoint.lstrip('/')
    url = f"{base_url}/{target_endpoint}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.error(f"Evolution API erro {e.code}: {error_body}")
        return {}
    except Exception as e:
        logger.error(f"Evolution API erro inesperado: {e}")
        return {}

def fetch_messages(count: int = 20) -> list:
    result = evolution_request(f"/chat/findMessages/{INSTANCE_NAME}", method="POST", data={"count": count})
    if isinstance(result, list): return result
    if isinstance(result, dict) and "messages" in result:
        data = result["messages"]
        return data.get("records", []) if isinstance(data, dict) else data
    return []

def send_whatsapp(phone: str, message: str) -> bool:
    result = evolution_request(f"/message/sendText/{INSTANCE_NAME}", method="POST", data={"number": phone, "text": message})
    success = bool(result.get("key") or result.get("id"))
    if success: logger.info(f"Enviado para {phone}")
    else: logger.error(f"Falha ao enviar para {phone}: {result}")
    return success

def extract_message_data(msg) -> dict:
    if not isinstance(msg, dict): return {}
    key = msg.get("key", {})
    if not isinstance(key, dict) or key.get("fromMe", False): return {}
    remote_jid = key.get("remoteJid", "")
    if "@g.us" in remote_jid: return {}
    
    phone = remote_jid.replace("@s.whatsapp.net", "").replace("@lid", "")
    if key.get("addressingMode") == "lid" and key.get("remoteJidAlt"):
        phone = key["remoteJidAlt"].replace("@s.whatsapp.net", "")
        
    push_name = msg.get("pushName", "Lead")
    content = msg.get("message", {})
    if not isinstance(content, dict): return {}
    
    text = content.get("conversation") or (content.get("extendedTextMessage") or {}).get("text") or ""
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
    logger.info("Watcher da Priscila iniciado")
    state = load_state()
    while True:
        try:
            messages = fetch_messages(count=20)
            for msg in messages:
                data = extract_message_data(msg)
                if not data or not data.get("phone") or not data.get("text"): continue
                if data["id"] in state["seen_ids"]: continue
                
                state["seen_ids"].append(data["id"])
                logger.info(f"📩 {data['name']} ({data['phone']}): {data['text'][:60]}")
                
                try:
                    response = handle_message(data["phone"], data["name"], data["text"])
                    if response: send_whatsapp(data["phone"], response)
                except Exception as e:
                    logger.error(f"Erro no processamento: {e}")
            
            save_state(state)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt: break
        except Exception as e:
            logger.error(f"Erro no loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    watch()
