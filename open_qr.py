
import base64
import tempfile
import os
import json
import urllib.request
from pathlib import Path

def get_qr():
    try:
        env_file = Path.home() / 'meu-agente' / 'evolution-api' / '.env'
        lines = env_file.read_text().splitlines()
        api_key = ""
        for line in lines:
            if line.startswith('AUTHENTICATION_API_KEY='):
                api_key = line.split('=')[1].strip().strip('"')
                break
        
        url = 'http://localhost:8080/instance/connect/meu-agente'
        req = urllib.request.Request(url, headers={'apikey': api_key})
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read())
            qr_data = res.get('base64') or res.get('qrcode', {}).get('base64')
            if not qr_data:
                print("Não foi possível obter o QR Code da API.")
                return
            
            img_path = Path(tempfile.gettempdir()) / 'agente-qrcode.png'
            img_path.write_bytes(base64.b64decode(qr_data.split(',')[-1]))
            os.startfile(str(img_path))
            print("✅ QR Code aberto! Por favor, escaneie no seu celular.")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == '__main__':
    get_qr()
