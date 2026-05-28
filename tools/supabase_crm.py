"""
tools/supabase_crm.py — Bot API integration for Lumière CRM.
Two tools: check_date_availability and create_lead.
"""
import os
import httpx
from datetime import datetime

BOT_API_URL = os.getenv("BOT_API_URL", "").rstrip("/")
BOT_API_KEY = os.getenv("BOT_API_KEY", "")


def _headers() -> dict:
    return {
        "x-bot-key": BOT_API_KEY,
        "Content-Type": "application/json",
    }


def _to_iso_date(date_str: str) -> str:
    """Convert dd.MM.yyyy / dd/MM/yyyy to yyyy-MM-dd."""
    if not date_str:
        return ""
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def check_date_availability(date: str) -> str:
    if not BOT_API_URL or not BOT_API_KEY:
        return "שירות הזמינות לא מחובר כרגע"

    iso_date = _to_iso_date(date)
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(
                BOT_API_URL,
                json={"action": "check_availability", "date": iso_date},
                headers=_headers()
            )
            r.raise_for_status()
            data = r.json()
            if data.get("available") is False:
                reason = data.get("reason", "תפוס")
                return f"התאריך {date} לא זמין ({reason})"
            return f"התאריך {date} פנוי"
    except Exception as e:
        return f"לא הצלחתי לבדוק זמינות: {e}"


def create_lead(
    chat_id: str,
    sender_name: str,
    event_type: str = "",
    date: str = "",
    guest_count: int = 0,
    location: str = "",
    event_time: str = "",
    allergies: str = "",
    has_children: bool = False,
    children_count: int = 0,
    notes: str = ""
) -> str:
    if not BOT_API_URL or not BOT_API_KEY:
        return "שירות ה-CRM לא מחובר כרגע"

    phone = chat_id.replace("@c.us", "").replace("@g.us", "")
    name = sender_name or "לא ידוע"
    iso_date = _to_iso_date(date) if date else ""

    # Fold extra details into notes
    extra = []
    if allergies:
        extra.append(f"אלרגיות: {allergies}")
    if has_children and children_count:
        extra.append(f"ילדים: {children_count}")
    if event_time:
        extra.append(f"שעה: {event_time}")
    if notes:
        extra.append(notes)
    full_notes = " | ".join(extra) if extra else "הגיע מהבוט בוואטסאפ"

    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(
                BOT_API_URL,
                json={
                    "action": "create_lead",
                    "name": name,
                    "phone": phone,
                    "date": iso_date,
                    "event_type": event_type or "",
                    "guest_count": int(guest_count) if guest_count else 0,
                    "location": location or "",
                    "notes": full_notes,
                },
                headers=_headers()
            )
            r.raise_for_status()
        return f"ליד נוצר ב-CRM: {name}"
    except Exception as e:
        return f"שגיאה ביצירת הליד: {e}"


def register(registry: dict) -> None:
    registry["check_date_availability"] = {
        "schema": {
            "name": "check_date_availability",
            "description": "בדוק אם תאריך מסוים פנוי לאירוע ביומן Lumière.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "התאריך בפורמט dd.MM.yyyy (לדוגמה: 15.08.2026)"
                    }
                },
                "required": ["date"]
            }
        },
        "fn": check_date_availability
    }

    registry["create_lead"] = {
        "schema": {
            "name": "create_lead",
            "description": "צור ליד חדש ב-CRM בסיום השיחה, אחרי שאספת את פרטי האירוע.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chat_id": {"type": "string", "description": "ימולא אוטומטית על ידי המערכת"},
                    "sender_name": {"type": "string", "description": "ימולא אוטומטית על ידי המערכת"},
                    "event_type": {"type": "string", "description": "סוג האירוע"},
                    "date": {"type": "string", "description": "תאריך האירוע בפורמט dd.MM.yyyy"},
                    "guest_count": {"type": "integer", "description": "מספר מוזמנים"},
                    "location": {"type": "string", "description": "מיקום האירוע"},
                    "event_time": {"type": "string", "description": "שעת האירוע"},
                    "allergies": {"type": "string", "description": "אלרגיות / תזונה מיוחדת"},
                    "has_children": {"type": "boolean", "description": "האם יהיו ילדים"},
                    "children_count": {"type": "integer", "description": "כמה ילדים"},
                    "notes": {"type": "string", "description": "הערות נוספות מהשיחה"}
                },
                "required": []
            }
        },
        "fn": create_lead
    }
