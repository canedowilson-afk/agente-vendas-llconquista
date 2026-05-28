import json
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime

ENV_FILE = Path.home() / "meu-agente" / ".env"


def load_env():
    values = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


ENV = load_env()
AI_PROVIDER = ENV.get("AI_PROVIDER", "gemini")
AI_MODEL = ENV.get("AI_MODEL", "gemini-2.5-flash")
AI_API_KEY = ENV.get("AI_API_KEY", "")

CHECKOUT_LINK = "https://wa.me/5543991853957"


def get_context_datetime():
    now = datetime.now()
    dias = ["Segunda-feira","Terca-feira","Quarta-feira",
            "Quinta-feira","Sexta-feira","Sabado","Domingo"]
    meses = ["janeiro","fevereiro","marco","abril","maio","junho",
             "julho","agosto","setembro","outubro","novembro","dezembro"]
    dia_semana = dias[now.weekday()]
    return (
        "Hoje e " + dia_semana + ", " +
        str(now.day) + " de " + meses[now.month-1] + " de " + str(now.year) + ". " +
        "Horario atual: " + now.strftime("%H:%M") + " (horario de Brasilia, GMT-3)."
    )


SYSTEM_PROMPT = """Voce e Marcia, secretaria da clinica odontologica Agente IA de Vendas para Clinicas Odontologicas.

Seu objetivo e entender a necessidade do paciente e conduzir a conversa ate o agendamento de uma avaliacao gratuita.

Contexto do negocio:
- Nicho: clinica odontologica especializada em transformar sorrisos
- Oferta principal: ajudar o lead a encontrar o melhor tratamento para o seu caso
- Oferta de entrada: avaliacao gratuita
- Tratamentos atendidos: limpeza, prevencao, implantes, ortodontia e estetica dental
- O investimento varia conforme a avaliacao do sorriso
- Existem horarios flexiveis e condicoes especiais de pagamento
- Qualquer novo contato no WhatsApp pode entrar no atendimento automatizado

Como se comportar:
- Responda sempre em portugues do Brasil.
- Seja cordial, humanizada, acolhedora e profissional.
- Use mensagens curtas, claras e naturais para WhatsApp.
- Escreva como Marcia, secretaria real da clinica, com empatia e educacao.
- Demonstre atencao ao contexto do paciente sem soar robotica ou mecanica.
- Nao invente procedimentos, precos ou condicoes que nao foram informados.
- Quando faltar um detalhe relevante, faca uma pergunta simples por vez.
- Nunca diga que e uma IA, a menos que o cliente pergunte diretamente.
- Quando fizer sentido, voce pode se apresentar como Marcia de forma natural, especialmente no inicio da conversa.
- Voce tem acesso ao horario e data atual. Use essa informacao quando relevante (ex: confirmar disponibilidade, dizer bom dia/boa tarde/boa noite corretamente).

Metodologia BANT:
- Need: descubra qual necessidade odontologica a pessoa quer resolver.
- Authority: confirme se a pessoa esta buscando consulta para si mesma ou para outra pessoa.
- Budget: como a avaliacao e gratuita, destaque isso cedo.
- Timeline: descubra quando a pessoa gostaria de agendar.

Regras de conversa:
- Na primeira resposta, cumprimente de forma natural com bom dia/boa tarde/boa noite conforme o horario atual.
- Na primeira resposta, apresente-se como Marcia, secretaria da clinica.
- Faca apenas uma pergunta por vez.
- Evite blocos longos.
- Se o lead demonstrar interesse real, convide para o agendamento.
- Se a conversa ja estiver madura, diga que vai enviar o link de agendamento.

Objetivo final:
- Levar o lead ate o agendamento da avaliacao gratuita.
"""


def call_ai(messages, max_tokens=512):
    context = get_context_datetime()
    messages_with_context = [{"role": "user", "content": "[CONTEXTO INTERNO - NAO MENCIONAR AO PACIENTE]: " + context}] + messages
    if AI_PROVIDER == "openai":
        return call_openai(messages_with_context, max_tokens)
    if AI_PROVIDER == "gemini":
        return call_gemini(messages_with_context, max_tokens)
    if AI_PROVIDER == "anthropic":
        return call_anthropic(messages_with_context, max_tokens)
    raise ValueError("Provider desconhecido: " + AI_PROVIDER)


def call_openai(messages, max_tokens):
    url = "https://api.openai.com/v1/chat/completions"
    data = {
        "model": AI_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "max_completion_tokens": max_tokens,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": "Bearer " + AI_API_KEY,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read())
        return result["choices"][0]["message"]["content"]


def call_gemini(messages, max_tokens):
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    data = {
        "model": AI_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "max_completion_tokens": max_tokens,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": "Bearer " + AI_API_KEY,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read())
        return result["choices"][0]["message"]["content"]


def call_anthropic(messages, max_tokens):
    url = "https://api.anthropic.com/v1/messages"
    data = {
        "model": AI_MODEL,
        "max_tokens": max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    headers = {
        "x-api-key": AI_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read())
        return result["content"][0]["text"]


def is_purchase_intent(message, conversation=None):
    if not message:
        return False
    message_lower = message.lower()
    purchase_keywords = [
        "quero",
        "agendar",
        "agendamento",
        "consulta",
        "avaliacao",
        "atendimento",
        "horario",
        "valor",
        "preco",
        "quanto",
        "custa",
    ]
    if any(keyword in message_lower for keyword in purchase_keywords):
        return True
    if conversation and len(conversation) >= 4:
        return True
    return False


def format_checkout_message():
    return (
        "Perfeito! Sua avaliacao e gratuita. Aqui esta o link para agendar:\n\n"
        + CHECKOUT_LINK
    )
