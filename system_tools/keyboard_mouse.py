"""
keyboard_mouse.py — Type text, press hotkeys, click, and move the mouse.
"""

import pyautogui

from langchain_core.tools import tool

from system_tools.safety import logger

# Disable pyautogui's failsafe pause so Jarvis feels snappy.
# The safety layer handles blocking dangerous operations.
pyautogui.PAUSE = 0.1


@tool
def type_text(text: str, interval: float = 0.02) -> str:
    """
    Type text at the current cursor position, as if typing on the keyboard.

    Args:
        text: The text string to type
        interval: Seconds between each keystroke (default 0.02)
    """
    try:
        pyautogui.typewrite(text, interval=interval) if text.isascii() else pyautogui.write(text)
        logger.log("type_text", {"text": text[:100]}, "Typed successfully")
        return f"✅ Typed: {text[:80]}{'...' if len(text) > 80 else ''}"
    except Exception as e:
        msg = f"❌ Failed to type text: {e}"
        logger.log("type_text", {"text": text[:100]}, msg, status="error")
        return msg


@tool
def press_hotkey(keys: str) -> str:
    """
    Press a keyboard shortcut / hotkey combination.

    Args:
        keys: Key combination separated by '+' (e.g. "ctrl+c", "alt+tab",
              "ctrl+shift+esc", "win+d", "enter", "f5")
    """
    try:
        key_list = [k.strip().lower() for k in keys.split("+")]
        pyautogui.hotkey(*key_list)
        logger.log("press_hotkey", {"keys": keys}, "Hotkey pressed")
        return f"✅ Pressed: {keys}"
    except Exception as e:
        msg = f"❌ Failed to press hotkey: {e}"
        logger.log("press_hotkey", {"keys": keys}, msg, status="error")
        return msg


@tool
def click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """
    Click the mouse at specific screen coordinates.

    Args:
        x: X coordinate on screen
        y: Y coordinate on screen
        button: Mouse button — "left", "right", or "middle" (default "left")
        clicks: Number of clicks (default 1, use 2 for double-click)
    """
    try:
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        logger.log("click_at", {"x": x, "y": y, "button": button, "clicks": clicks}, "Clicked")
        return f"✅ Clicked ({button}) at ({x}, {y}) x{clicks}"
    except Exception as e:
        msg = f"❌ Failed to click: {e}"
        logger.log("click_at", {"x": x, "y": y}, msg, status="error")
        return msg


@tool
def move_mouse(x: int, y: int, duration: float = 0.3) -> str:
    """
    Move the mouse cursor to specific screen coordinates.

    Args:
        x: Target X coordinate
        y: Target Y coordinate
        duration: Seconds to take for the move animation (default 0.3)
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        logger.log("move_mouse", {"x": x, "y": y}, "Mouse moved")
        return f"✅ Mouse moved to ({x}, {y})"
    except Exception as e:
        msg = f"❌ Failed to move mouse: {e}"
        logger.log("move_mouse", {"x": x, "y": y}, msg, status="error")
        return msg
