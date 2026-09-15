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

def get_chat_history(chat_id: str, count: int = 25) -> list:
    """Fetch recent WhatsApp messages for a chat. Raises on API failure."""
    url = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE}/getChatHistory/{GREEN_API_TOKEN}"
    resp = httpx.post(url, json={"chatId": chat_id, "count": count}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def has_prior_history(chat_id: str, fresh_window_sec: int = 300) -> bool:
    """
    True if this contact is NOT new — i.e. we already corresponded with them.

    A contact counts as known when the chat contains any outgoing message,
    or any message older than the current burst (fresh_window_sec).
    On API failure we return True, so the bot stays silent rather than
    greeting someone who is already a customer.
    """
    import logging
    import time

    try:
        messages = get_chat_history(chat_id)
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"getChatHistory failed for {chat_id}: {e} — treating as known contact"
        )
        return True

    now = time.time()
    for m in messages:
        if not isinstance(m, dict):
            continue
        if m.get("type") == "outgoing":
            return True
        ts = m.get("timestamp") or 0
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            continue
        if ts and (now - ts) > fresh_window_sec:
            return True
    return False
