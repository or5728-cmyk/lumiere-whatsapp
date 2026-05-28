"""
tools/supabase_crm.py — Supabase CRM integration for Lumière.
Two tools: check_date_availability and create_lead.
"""
import os
import httpx
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
ASSIGNED_TO = os.getenv("SUPABASE_ASSIGNED_TO", "367654fb-e54f-4cda-b452-19c3e1c0e690")


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _to_iso_date(date_str: str) -> str:
    """Convert dd.MM.yyyy / dd/MM/yyyy / d.M.yyyy to yyyy-MM-dd."""
    if not date_str:
        return ""
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def check_date_availability(date: str) -> str:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return "שירות הזמינות לא מחובר כרגע"

    iso_date = _to_iso_date(date)
    try:
        with httpx.Client(timeout=10) as client:
            # Check blocked days first
            r = client.get(
                f"{SUPABASE_URL}/rest/v1/blocked_days",
                params={"date": f"eq.{iso_date}"},
                headers=_headers()
            )
            r.raise_for_status()
            blocked = r.json()
            if blocked:
                reason = blocked[0].get("reason", "") or "חסום"
                return f"התאריך {date} חסום ({reason}) - לא זמינים"

            # Check existing events
            r2 = client.get(
                f"{SUPABASE_URL}/rest/v1/events",
                params={
                    "date": f"eq.{iso_date}",
                    "archived_at": "is.null",
                    "status": "neq.cancelled",
                },
                headers=_headers()
            )
            r2.raise_for_status()
            events = r2.json()
            if events:
                return f"התאריך {date} תפוס - יש כבר אירוע ביומן. כדאי לבדוק עם הצוות"

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
    if not SUPABASE_URL or not SUPABASE_KEY:
        return "שירות ה-CRM לא מחובר כרגע"

    phone = chat_id.replace("@c.us", "").replace("@g.us", "")
    name = sender_name or "לא ידוע"
    iso_date = _to_iso_date(date) if date else ""

    try:
        with httpx.Client(timeout=10) as client:
            # 1. Create customer
            r_cust = client.post(
                f"{SUPABASE_URL}/rest/v1/customers",
                json={
                    "name": name,
                    "phone": phone,
                    "city": location or "",
                    "lead_source": "whatsapp",
                    "assigned_to": ASSIGNED_TO,
                    "notes": notes or "",
                },
                headers=_headers()
            )
            r_cust.raise_for_status()
            customer_id = r_cust.json()[0]["id"]

            # 2. Create event
            r_evt = client.post(
                f"{SUPABASE_URL}/rest/v1/events",
                json={
                    "customer_id": customer_id,
                    "customer_name": name,
                    "date": iso_date,
                    "time": event_time or "",
                    "event_type": event_type or "",
                    "guest_count": int(guest_count) if guest_count else 30,
                    "location": location or "",
                    "status": "lead",
                    "assigned_to": ASSIGNED_TO,
                    "has_children": bool(has_children),
                    "children_count": int(children_count) if children_count else 0,
                    "allergies": allergies or "",
                    "notes": notes or "",
                    "deposit_paid": False,
                },
                headers=_headers()
            )
            r_evt.raise_for_status()

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
                        "description": "התאריך בפורמט dd.MM.yyyy (לדוגמה: 15.08.2025)"
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
