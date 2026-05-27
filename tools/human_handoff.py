"""
Human handoff tool — notifies the business owner when a lead wants to be contacted.
Sends a lead summary to the manager's phone via WhatsApp.
"""
import json
from config import SPEC


def request_human_handoff(
    chat_id: str,
    sender_name: str,
    event_type: str = "",
    guests: str = "",
    location: str = "",
    date: str = "",
    notes: str = ""
) -> str:
    """
    Notify the business manager that a lead wants to be contacted.
    Use this when a customer asks for a call, a human agent, or a price quote callback.
    chat_id will be filled by the framework; leave empty.
    """
    from tools.whatsapp import send_to_phone

    handoff = SPEC.get("handoff", {})
    manager_phone = handoff.get("manager_phone", "")

    if not manager_phone:
        return "לא הוגדר מספר נציג — לא נשלחה הודעה"

    # Build lead summary
    sender_phone = chat_id.replace("@c.us", "").replace("@g.us", "")

    summary_lines = [
        "🌸 ליד חדש מ-Lumière",
        f"שם: {sender_name}",
        f"מספר: {sender_phone}",
    ]
    if event_type:
        summary_lines.append(f"אירוע: {event_type}")
    if guests:
        summary_lines.append(f"מוזמנים: {guests}")
    if location:
        summary_lines.append(f"מיקום: {location}")
    if date:
        summary_lines.append(f"תאריך: {date}")
    if notes:
        summary_lines.append(f"הערות: {notes}")

    wa_link = f"https://wa.me/{sender_phone}"
    summary_lines.append(f"קישור לשיחה: {wa_link}")

    summary = "\n".join(summary_lines)

    try:
        send_to_phone(manager_phone, summary)
        return "הליד נשלח לנציגה בהצלחה"
    except Exception as e:
        return f"שגיאה בשליחת הליד: {e}"


def register(registry: dict) -> None:
    registry["request_human_handoff"] = {
        "schema": {
            "name": "request_human_handoff",
            "description": "שלח פרטי ליד לנציגת המכירות כשלקוח מבקש שיחה חזרה, נציג אנושי, או הצעת מחיר.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "chat_id will be filled by the framework; leave empty"
                    },
                    "sender_name": {
                        "type": "string",
                        "description": "שם הלקוח מהוואטסאפ"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "סוג האירוע שהלקוח ציין"
                    },
                    "guests": {
                        "type": "string",
                        "description": "מספר מוזמנים שהלקוח ציין"
                    },
                    "location": {
                        "type": "string",
                        "description": "מיקום האירוע"
                    },
                    "date": {
                        "type": "string",
                        "description": "תאריך האירוע"
                    },
                    "notes": {
                        "type": "string",
                        "description": "הערות נוספות מהשיחה"
                    }
                },
                "required": ["chat_id", "sender_name"]
            }
        },
        "fn": request_human_handoff
    }
