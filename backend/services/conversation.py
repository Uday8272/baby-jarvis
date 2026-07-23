from backend.models import Message


def build_prompt_with_memory(user_text: str, recent_messages: list[Message]) -> str:
    instruction = (
        "You are JARVIS, a precise and security-conscious assistant for your owner. "
        "Use conversation history for context, but prioritize the most recent user request."
    )
    history_lines = []
    for item in recent_messages:
        speaker = "User" if item.role == "user" else "Jarvis"
        history_lines.append(f"{speaker}: {item.content}")

    history_block = "\n".join(history_lines) if history_lines else "(no previous messages)"
    return (
        f"{instruction}\n\n"
        f"Conversation history:\n{history_block}\n\n"
        f"Current user message:\nUser: {user_text}\n\n"
        "Respond as Jarvis:"
    )
