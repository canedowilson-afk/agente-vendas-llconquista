from flask import Flask, request, jsonify
import sys
import logging
from pathlib import Path

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Importar lógica do agente
sys.path.insert(0, str(Path(__file__).parent))
from agent import handle_message
import watcher # para reutilizar send_whatsapp

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400
    
    event = data.get('event')
    if event == 'messages.upsert':
        msg_list = data.get('data', {}).get('messages', [])
        for msg in msg_list:
            msg_data = watcher.extract_message_data(msg)
            if not msg_data or not msg_data.get('phone') or not msg_data.get('text'):
                continue
            
            phone, name, text = msg_data['phone'], msg_data['name'], msg_data['text']
            logger.info(f"📩 Recebido de {name} ({phone}): {text[:60]}")
            
            try:
                response = handle_message(phone, name, text)
                if response:
                    watcher.send_whatsapp(phone, response)
            except Exception as e:
                logger.error(f"Erro ao processar: {e}")
                
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    logger.info("🚀 Webhook Server iniciado na porta 5000")
    app.run(host='0.0.0.0', port=5000)
