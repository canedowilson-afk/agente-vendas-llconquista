import json
import urllib.request

url = "http://localhost:8080/webhook/set/meu-agente"
headers = {
    "apikey": "21D1472B-D5BD-42BB-8257-CE31744CCF3A",
    "Content-Type": "application/json"
}
data = {
    "url": "http://host.docker.internal:5000/webhook",
    "enabled": True,
    "events": ["messages.upsert"]
}

req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(f"Erro: {e}")
