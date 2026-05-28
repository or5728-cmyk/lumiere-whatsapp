import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val

# Green API
GREEN_API_URL = _require("GREEN_API_URL").rstrip("/")
GREEN_API_INSTANCE = _require("GREEN_API_INSTANCE")
GREEN_API_TOKEN = _require("GREEN_API_TOKEN")

# LLM
LLM_PROVIDER = _require("LLM_PROVIDER")   # anthropic / openai / google
LLM_MODEL = _require("LLM_MODEL")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
    raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is missing")
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is missing")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/conversations.db")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))

# Supabase CRM (optional — tools only activate when both are set)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ASSIGNED_TO = os.getenv("SUPABASE_ASSIGNED_TO", "367654fb-e54f-4cda-b452-19c3e1c0e690")

# Spec
_spec_path = Path(__file__).parent / "spec.json"
if not _spec_path.exists():
    raise RuntimeError("spec.json not found — run wa-characterize first")

with open(_spec_path, encoding="utf-8") as f:
    SPEC = json.load(f)
