"""
WhatsApp sending helpers — framework only, not an LLM tool.
Used by main.py and other tools to send messages.
"""
import httpx

from config import GREEN_API_URL, GREEN_API_INSTANCE, GREEN_API_TOKEN


def send_reply(chat_id: str, text: str) -> None:
    """Send a text message to a WhatsApp chat (chatId format: 972XXXXXXXXX@c.us)."""
    url = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
    payload = {"chatId": chat_id, "message": text}
    resp = httpx.post(url, json=payload, timeout=15)
    resp.raise_for_status()


def send_to_phone(phone_e164: str, text: str) -> None:
    """Send a message to a phone number in E.164 format (e.g. '972501234567')."""
    chat_id = f"{phone_e164}@c.us"
    send_reply(chat_id, text)
