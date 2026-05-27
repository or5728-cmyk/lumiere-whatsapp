"""
main.py — FastAPI app.
Receives webhooks from Green API, filters messages, calls agent, sends reply.
"""
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent import handle_message
from config import GREEN_API_INSTANCE, SPEC
from database import init_db, is_processed, mark_processed
from tools.whatsapp import send_reply

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Lumière WhatsApp Bot")

# The bot's own JID — messages from self should be ignored
OWN_JID = f"{GREEN_API_INSTANCE}@c.us"

# Business hours from spec
_hours = SPEC.get("business_hours", {})
_HOUR_START = int(_hours.get("start", "07:00").split(":")[0])
_HOUR_END = int(_hours.get("end", "21:00").split(":")[0])
_OFF_HOURS_MSG = _hours.get("off_hours_message", "נחזור אליכם בשעות הפעילות.")
_OFF_HOURS_MODE = SPEC.get("extras", {}).get("off_hours_mode", "always_reply")

# Audience settings
_ANSWER_GROUPS = SPEC.get("audience", {}).get("answer_groups", False)
_AUDIENCE_MODE = SPEC.get("audience", {}).get("mode", "public")
_AUTHORIZED_CONTACTS = {
    c["phone_e164"] for c in SPEC.get("audience", {}).get("authorized_contacts", [])
}


_TZ = ZoneInfo(SPEC.get("business_hours", {}).get("timezone", "Asia/Jerusalem"))


def _is_business_hours() -> bool:
    now = datetime.now(_TZ).hour
    return _HOUR_START <= now < _HOUR_END


def _is_authorized(sender_phone: str) -> bool:
    if _AUDIENCE_MODE == "public":
        return True
    # whitelist mode — personal assistant
    return sender_phone in _AUTHORIZED_CONTACTS


@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Lumière bot started ✨")


@app.get("/health")
async def health():
    return {"status": "ok", "bot": "Lumière", "version": 1}


@app.post("/webhook/green-api")
async def webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "detail": "invalid JSON"}, status_code=400)

    webhook_type = body.get("typeWebhook")

    # Only handle incoming text/media messages
    if webhook_type != "incomingMessageReceived":
        return JSONResponse({"status": "ignored", "reason": "not incomingMessageReceived"})

    id_message = body.get("idMessage", "")
    sender_data = body.get("senderData", {})
    message_data = body.get("messageData", {})

    chat_id = sender_data.get("chatId", "")
    sender_name = sender_data.get("senderName", "")
    sender_id = sender_data.get("sender", "")

    # Ignore own messages
    if sender_id == OWN_JID or chat_id == OWN_JID:
        return JSONResponse({"status": "ignored", "reason": "own message"})

    # Ignore group messages if configured
    if chat_id.endswith("@g.us") and not _ANSWER_GROUPS:
        return JSONResponse({"status": "ignored", "reason": "group message"})

    # Deduplicate
    if id_message and is_processed(id_message):
        return JSONResponse({"status": "ignored", "reason": "already processed"})

    # Authorize sender
    sender_phone = chat_id.replace("@c.us", "").replace("@g.us", "")
    if not _is_authorized(sender_phone):
        logger.info(f"Unauthorized sender: {sender_phone}")
        return JSONResponse({"status": "ignored", "reason": "not authorized"})

    # Parse message text
    msg_type = message_data.get("typeMessage", "")

    if msg_type == "textMessage":
        message_text = message_data.get("textMessageData", {}).get("textMessage", "")
    elif msg_type in ("audioMessage", "voiceMessage", "pttMessage"):
        message_text = "__voice__"
    elif msg_type in ("imageMessage", "videoMessage", "documentMessage"):
        message_text = "__image__"
    else:
        message_text = message_data.get("textMessageData", {}).get("textMessage", "")

    if not message_text:
        return JSONResponse({"status": "ignored", "reason": "empty message"})

    # Handle unsupported types before LLM call
    unsupported = SPEC.get("unsupported_messages", {})
    if message_text == "__voice__":
        reply = "אני לא יכולה לשמוע כרגע, אשמע יותר מאוחר או שנשוחח בהודעות 😊"
        send_reply(chat_id, reply)
        if id_message:
            mark_processed(id_message)
        return JSONResponse({"status": "ok"})

    if message_text == "__image__":
        reply = unsupported.get("image", "תודה על התמונה! ספרי לי קצת על האירוע בטקסט 🌸")
        send_reply(chat_id, reply)
        if id_message:
            mark_processed(id_message)
        return JSONResponse({"status": "ok"})

    # Business hours check
    if _OFF_HOURS_MODE == "business_hours_only" and not _is_business_hours():
        send_reply(chat_id, _OFF_HOURS_MSG)
        if id_message:
            mark_processed(id_message)
        return JSONResponse({"status": "ok", "reason": "off hours"})

    # Mark as processed before calling LLM (prevents double-processing on crash)
    if id_message:
        mark_processed(id_message)

    try:
        reply = handle_message(chat_id, sender_name, message_text)
        send_reply(chat_id, reply)
        logger.info(f"Replied to {chat_id}: {reply[:60]}...")
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        send_reply(chat_id, "אוי, קרתה תקלה קטנה 😅 נחזור אליכם עוד רגע!")

    return JSONResponse({"status": "ok"})
