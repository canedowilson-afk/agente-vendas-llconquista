#!/usr/bin/env python3
"""
agent.py — Agente WhatsApp completo
"""

import sys
import os
from pathlib import Path

# Adicionar diretório atual ao path para importações
sys.path.insert(0, str(Path(__file__).parent))

from agent_core import call_ai, is_purchase_intent, format_checkout_message
from sessions import init_db, load_session, save_session, create_lead, add_message, mark_checkout_sent

def is_trigger(text: str) -> bool:
    """Responde a qualquer mensagem que não esteja vazia."""
    return len(text.strip()) > 0

def handle_message(phone: str, sender_name: str, text: str) -> str:
    if not is_trigger(text):
        return None

    lead_id = create_lead(phone, name=sender_name)
    messages = load_session(lead_id) or []

    user_message = {"role": "user", "content": text}
    messages.append(user_message)
    add_message(lead_id, "user", text)

    response = call_ai(messages)

    assistant_message = {"role": "assistant", "content": response}
    messages.append(assistant_message)
    add_message(lead_id, "assistant", response)

    save_session(lead_id, messages)

    # Injetar checkout se detectada intenção de compra
    if is_purchase_intent(text, messages) and len(messages) >= 2:
        response += f"\n\n{format_checkout_message()}"
        mark_checkout_sent(lead_id)

    return response

if __name__ == "__main__":
    init_db()
    if len(sys.argv) > 1 and sys.argv[1] == "--chat":
        phone = "teste_cli"
        print(f"Chat iniciado com {phone}. Digite 'sair' para encerrar.")
        while True:
            msg = input("Você: ")
            if msg.lower() == "sair": break
            res = handle_message(phone, "Usuário Teste", msg)
            print(f"Priscila: {res}")
