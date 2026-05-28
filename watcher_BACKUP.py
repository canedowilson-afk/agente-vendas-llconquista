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

# Caminhos
BASE_DIR = Path(__file__).parent.absolute()
STATE_FILE = BASE_DIR / "watcher_state.json"
LOG_PATH = BASE_DIR / "watcher.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH, encoding='utf-8')]
)
logger = logging.getLogger(__name__)

# Importar lógica da IA
sys.path.insert(0, str(BASE_DIR))
try:
    from agent import handle_message
except ImportError:
    logger.error("❌ Arquivo agent.py não encontrado!")
    sys.exit(1)

# CONFIGURAÇÕES
URL = "https://shadeseekingbeardeddragon-evolution.cloudfy.live"
KEY = "P3dWbqgib0UrubYUtIeK2A1sBdn4QUEU"
NAME = "Arlete"
POLL_INTERVAL = 3

def api_call(path, method='GET', data=None):
    url = f"{URL}{path}"
    headers = {'apikey': KEY, 'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def watch():
    logger.info(f"🦅 AGENTE VIVO! Monitorando instância: {NAME}")
    
    # Carregar estado (mensagens já vistas)
    state = {'seen_ids': []}
    if STATE_FILE.exists():
        try: state = json.loads(STATE_FILE.read_text())
        except: pass

    while True:
        try:
            # Busca mensagens forçando a leitura (fetchMessages)
            res = api_call(f"/message/fetchMessages/{NAME}", method='POST', data={'count': 5})
            
            # Se vier vazio ou der erro, tentamos o findMessages como plano B
            if not res or (isinstance(res, dict) and "error" in res):
                res = api_call(f"/chat/findMessages/{NAME}", method='POST', data={'count': 5})
            
            messages = []
            if isinstance(res, list): messages = res
            elif isinstance(res, dict) and 'messages' in res: messages = res['messages']

            for msg in messages:
                if not isinstance(msg, dict): continue
                
                # Pegar ID e verificar se já vimos
                msg_id = msg.get('key', {}).get('id')
                if not msg_id or msg_id in state['seen_ids']: continue
                
                # Ignorar se for minha
                if msg.get('key', {}).get('fromMe'):
                    state['seen_ids'].append(msg_id)
                    continue

                # Ignorar mensagens muito velhas (mais de 1 hora)
                ts = msg.get('messageTimestamp')
                if ts and (time.time() - float(ts)) > 3600:
                    state['seen_ids'].append(msg_id)
                    continue

                # Extrair dados
                remote_jid = msg.get('key', {}).get('remoteJid', '')
                if '@g.us' in remote_jid: continue # Ignora grupos
                
                phone = remote_jid.split('@')[0]
                push_name = msg.get('pushName', 'Cliente')
                
                msg_content = msg.get('message', {})
                text = msg_content.get('conversation') or \
                       (msg_content.get('extendedTextMessage', {}) or {}).get('text') or ''

                if not text.strip(): continue

                # AGORA O ROBÔ RESPONDE!
                logger.info(f"📩 Mensagem de {push_name}: {text[:30]}...")
                state['seen_ids'].append(msg_id)
                
                try:
                    # Chama a IA para gerar a resposta
                    response = handle_message(phone, push_name, text)
                    if response:
                        # Envia para o WhatsApp
                        send_res = api_call(f"/message/sendText/{NAME}", method='POST', data={'number': phone, 'text': response})
                        if send_res.get('key') or send_res.get('id'):
                            logger.info(f"✅ Resposta enviada com sucesso!")
                        else:
                            logger.error(f"❌ Falha ao enviar: {send_res}")
                except Exception as e:
                    logger.error(f"Erro ao processar com IA: {e}")
            
            # Salvar progresso
            if len(state['seen_ids']) > 1000: state['seen_ids'] = state['seen_ids'][-1000:]
            STATE_FILE.write_text(json.dumps(state, indent=2))
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt: break
        except Exception as e:
            logger.error(f"Erro no loop: {e}")
            time.sleep(5)

if __name__ == '__main__':
    watch()
