import json
import time
import logging
import sys
import io
import urllib.request
import urllib.error
from pathlib import Path

# UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent.absolute()
STATE_FILE = BASE_DIR / "watcher_state_v2.json"
LOG_PATH = BASE_DIR / "watcher_v2.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH, encoding='utf-8')]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(BASE_DIR))
try:
    from agent import handle_message
except ImportError:
    logger.error("Arquivo agent.py nao encontrado!")
    sys.exit(1)

URL = "https://shadeseekingbeardeddragon-evolution.cloudfy.live"
KEY = "P3dWbqgib0UrubYUtIeK2A1sBdn4QUEU"
NAME = "Arlete"
POLL_INTERVAL = 5

def api_call(path, method='GET', data=None):
    url = f"{URL}{path}"
    headers = {'apikey': KEY, 'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def watch():
    logger.info("=" * 60)
    logger.info(f"WATCHER V2 - MODO DEBUG TOTAL")
    logger.info(f"Instancia: {NAME}")
    logger.info("=" * 60)

    state = {'seen_ids': []}
    if STATE_FILE.exists():
        try: state = json.loads(STATE_FILE.read_text())
        except: pass

    loop_count = 0

    while True:
        try:
            loop_count += 1
            logger.info(f"--- LOOP #{loop_count} ---")
            
            res = api_call(
                f"/chat/findMessages/{NAME}",
                method='POST',
                data={'where': {}}
            )

            # DEBUG: mostra a estrutura da resposta
            logger.info(f"Tipo da resposta: {type(res).__name__}")
            
            if isinstance(res, dict):
                logger.info(f"Chaves da resposta: {list(res.keys())}")
                
                if 'error' in res:
                    logger.error(f"ERRO da API: {res['error']}")
                    time.sleep(POLL_INTERVAL)
                    continue
                
                if 'messages' in res:
                    msg_obj = res['messages']
                    logger.info(f"Tipo de 'messages': {type(msg_obj).__name__}")
                    
                    if isinstance(msg_obj, dict):
                        logger.info(f"Chaves de 'messages': {list(msg_obj.keys())}")
                        
                        if 'records' in msg_obj:
                            records = msg_obj['records']
                            logger.info(f"TOTAL DE MENSAGENS: {len(records)}")
                            
                            # Mostra as 3 ultimas
                            for i, msg in enumerate(records[-3:]):
                                if isinstance(msg, dict):
                                    msg_id = msg.get('key', {}).get('id', 'N/A')
                                    from_me = msg.get('key', {}).get('fromMe', False)
                                    push_name = msg.get('pushName', 'N/A')
                                    ts = msg.get('messageTimestamp', 'N/A')
                                    
                                    msg_content = msg.get('message', {}) or {}
                                    text = msg_content.get('conversation') or \
                                           (msg_content.get('extendedTextMessage', {}) or {}).get('text') or '(sem texto)'
                                    
                                    logger.info(f"  MSG {i+1}: id={msg_id[:15]}... fromMe={from_me} de={push_name} ts={ts} texto={text[:40]}")
            else:
                logger.warning(f"Resposta nao e dict: {str(res)[:200]}")

            logger.info(f"Aguardando {POLL_INTERVAL}s ate proximo loop...")
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Watcher interrompido pelo usuario")
            break
        except Exception as e:
            logger.error(f"Erro no loop: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    watch()
