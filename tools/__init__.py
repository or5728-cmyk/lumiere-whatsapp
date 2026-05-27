# TOOL_REGISTRY maps tool name → {"schema": <LLM tool schema>, "fn": <callable>}
# Tools are registered here on import. wa-connect adds more tools over time.

TOOL_REGISTRY: dict = {}

# Import tools that are always available
from tools.human_handoff import register  # noqa: E402
register(TOOL_REGISTRY)
