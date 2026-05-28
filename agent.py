"""
agent.py — LLM call + tool-calling loop.
Single entry point: handle_message(chat_id, sender_name, message_text) -> reply_text
"""
import anthropic

from config import ANTHROPIC_API_KEY, LLM_MODEL, MAX_HISTORY, SPEC
from database import append, tail
from prompt import build_system_prompt
from tools import TOOL_REGISTRY

# Tools whose chat_id must be injected by the framework, not chosen by the LLM.
FRAMEWORK_INJECTED_CHAT_ID = {
    "request_human_handoff",
    "schedule_reminder",
    "list_reminders",
    "cancel_reminder",
    "create_lead",
}

# Tools that also need sender_name injected by the framework.
FRAMEWORK_INJECTED_SENDER_NAME = {
    "create_lead",
}

MAX_TOOL_ITERATIONS = 5

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _run_tool(tool_use, chat_id: str, sender_name: str = "") -> str:
    """Execute a tool call and return a string result."""
    tool_name = tool_use.name
    if tool_name not in TOOL_REGISTRY:
        return f"כלי '{tool_name}' לא נמצא"

    tool_def = TOOL_REGISTRY[tool_name]
    tool_input = dict(tool_use.input or {})

    # Framework injects chat_id and optionally sender_name — LLM values are overridden
    if tool_name in FRAMEWORK_INJECTED_CHAT_ID:
        tool_input["chat_id"] = chat_id
    if tool_name in FRAMEWORK_INJECTED_SENDER_NAME:
        tool_input["sender_name"] = sender_name

    try:
        result = tool_def["fn"](**tool_input)
        return str(result)
    except Exception as e:
        return f"שגיאה בהרצת הכלי: {e}"


def handle_message(chat_id: str, sender_name: str, message_text: str) -> str:
    """
    Process an incoming WhatsApp message and return a reply.
    Saves conversation to DB.
    """
    system_prompt = build_system_prompt(SPEC, TOOL_REGISTRY)

    # Load history + append the new user message
    history = tail(chat_id, MAX_HISTORY)
    history.append({"role": "user", "content": message_text})

    # Build LLM tools list from registry
    tools_for_llm = [td["schema"] for td in TOOL_REGISTRY.values()]

    messages = list(history)
    reply_text = ""

    for iteration in range(MAX_TOOL_ITERATIONS):
        kwargs = {
            "model": LLM_MODEL,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": messages,
        }
        if tools_for_llm:
            kwargs["tools"] = tools_for_llm

        response = _client.messages.create(**kwargs)

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract text reply
            for block in response.content:
                if hasattr(block, "text"):
                    reply_text = block.text
                    break
            break

        elif response.stop_reason == "tool_use":
            # Append assistant message
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _run_tool(block, chat_id, sender_name)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason — extract whatever text we have
            for block in response.content:
                if hasattr(block, "text"):
                    reply_text = block.text
                    break
            break

    else:
        # Hit iteration cap
        reply_text = "תודה על פנייתך! נחזור אליך בהקדם 🌸"

    if not reply_text:
        reply_text = "תודה על פנייתך! נחזור אליך בהקדם 🌸"

    # Persist to DB
    append(chat_id, "user", message_text)
    append(chat_id, "assistant", reply_text)

    return reply_text
