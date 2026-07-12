"""
clipboard.py — Read and write system clipboard.
"""

import pyperclip

from langchain_core.tools import tool

from system_tools.safety import logger


@tool
def get_clipboard() -> str:
    """
    Read the current text content from the system clipboard.

    Returns the clipboard text or a message if the clipboard is empty.
    """
    try:
        content = pyperclip.paste()
        if not content:
            return "📋 Clipboard is empty."
        logger.log("get_clipboard", {}, f"Read {len(content)} chars")
        return f"📋 Clipboard contents:\n{content}"
    except Exception as e:
        msg = f"❌ Failed to read clipboard: {e}"
        logger.log("get_clipboard", {}, msg, status="error")
        return msg


@tool
def set_clipboard(text: str) -> str:
    """
    Copy text to the system clipboard, replacing existing clipboard content.

    Args:
        text: The text to copy to the clipboard
    """
    try:
        pyperclip.copy(text)
        logger.log("set_clipboard", {"text": text[:100]}, "Clipboard set")
        return f"✅ Copied to clipboard ({len(text)} characters)"
    except Exception as e:
        msg = f"❌ Failed to set clipboard: {e}"
        logger.log("set_clipboard", {"text": text[:100]}, msg, status="error")
        return msg
