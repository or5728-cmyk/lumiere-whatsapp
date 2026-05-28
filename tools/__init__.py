# TOOL_REGISTRY maps tool name → {"schema": <LLM tool schema>, "fn": <callable>}
# Tools are registered here on import. wa-connect adds more tools over time.

TOOL_REGISTRY: dict = {}

# Import tools that are always available
from tools.human_handoff import register  # noqa: E402
register(TOOL_REGISTRY)

# Register Supabase CRM tools only when env vars are configured
import os as _os
if _os.getenv("SUPABASE_URL") and _os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
    from tools.supabase_crm import register as _register_crm  # noqa: E402
    _register_crm(TOOL_REGISTRY)
