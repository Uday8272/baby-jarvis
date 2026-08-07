"""
screen.py — Screenshot capture.
"""

import os
import time
from pathlib import Path

from langchain_core.tools import tool

from agent.tools.safety import logger


from backend.config import get_settings
settings = get_settings()
SCREENSHOT_DIR = Path(settings.jarvis_screenshot_dir)


@tool
def take_screenshot(save_path: str = "") -> str:
    """
    Capture a screenshot of the entire screen and save it as a PNG.

    Returns the path to the saved screenshot file.

    Args:
        save_path: Optional custom save path. If empty, saves to the
                   screenshots directory with a timestamp name.
    """
    try:
        import pyautogui

        if save_path:
            p = Path(save_path).resolve()
        else:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            p = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"

        p.parent.mkdir(parents=True, exist_ok=True)

        screenshot = pyautogui.screenshot()
        screenshot.save(str(p))

        logger.log("take_screenshot", {"save_path": str(p)}, f"Screenshot saved: {p}")
        return f"✅ Screenshot saved: {p}"
    except Exception as e:
        msg = f"❌ Failed to take screenshot: {e}"
        logger.log("take_screenshot", {"save_path": save_path}, msg, status="error")
        return msg
