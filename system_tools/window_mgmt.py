"""
window_mgmt.py — List, focus, minimize, maximize, and close windows.

Uses pygetwindow (cross-platform wrapper) which is already installed
as a pyautogui dependency.
"""

import pygetwindow as gw

from langchain_core.tools import tool

from system_tools.safety import logger


@tool
def list_windows() -> str:
    """
    List all visible (non-empty-title) windows currently open on the desktop.

    Returns window titles with their positions and sizes.
    """
    try:
        windows = [w for w in gw.getAllWindows() if w.title.strip()]
        if not windows:
            return "🪟 No visible windows found."

        lines = ["🪟 Open Windows:\n"]
        for i, w in enumerate(windows, 1):
            lines.append(f"  {i}. {w.title}")
            lines.append(f"     Position: ({w.left}, {w.top}) | Size: {w.width}x{w.height}")

        result = "\n".join(lines)
        logger.log("list_windows", {}, f"{len(windows)} windows")
        return result
    except Exception as e:
        msg = f"❌ Error listing windows: {e}"
        logger.log("list_windows", {}, msg, status="error")
        return msg


def _find_window(title: str):
    """Find the best-matching window by (partial) title."""
    # Try exact match first
    exact = gw.getWindowsWithTitle(title)
    if exact:
        return exact[0]

    # Try case-insensitive partial match
    for w in gw.getAllWindows():
        if title.lower() in w.title.lower():
            return w

    return None


@tool
def focus_window(title: str) -> str:
    """
    Bring a window to the foreground by its title (partial match supported).

    Args:
        title: Full or partial window title (e.g. "Chrome", "Visual Studio Code")
    """
    try:
        w = _find_window(title)
        if not w:
            return f"⚠️ No window found matching: '{title}'"

        if w.isMinimized:
            w.restore()
        w.activate()
        logger.log("focus_window", {"title": title}, f"Focused: {w.title}")
        return f"✅ Focused window: {w.title}"
    except Exception as e:
        msg = f"❌ Error focusing window: {e}"
        logger.log("focus_window", {"title": title}, msg, status="error")
        return msg


@tool
def minimize_window(title: str) -> str:
    """
    Minimize a window by its title (partial match supported).

    Args:
        title: Full or partial window title
    """
    try:
        w = _find_window(title)
        if not w:
            return f"⚠️ No window found matching: '{title}'"
        w.minimize()
        logger.log("minimize_window", {"title": title}, f"Minimized: {w.title}")
        return f"✅ Minimized: {w.title}"
    except Exception as e:
        msg = f"❌ Error minimizing window: {e}"
        logger.log("minimize_window", {"title": title}, msg, status="error")
        return msg


@tool
def maximize_window(title: str) -> str:
    """
    Maximize a window by its title (partial match supported).

    Args:
        title: Full or partial window title
    """
    try:
        w = _find_window(title)
        if not w:
            return f"⚠️ No window found matching: '{title}'"
        w.maximize()
        logger.log("maximize_window", {"title": title}, f"Maximized: {w.title}")
        return f"✅ Maximized: {w.title}"
    except Exception as e:
        msg = f"❌ Error maximizing window: {e}"
        logger.log("maximize_window", {"title": title}, msg, status="error")
        return msg


@tool
def close_window(title: str) -> str:
    """
    Close a window by its title (partial match supported).

    Args:
        title: Full or partial window title
    """
    try:
        w = _find_window(title)
        if not w:
            return f"⚠️ No window found matching: '{title}'"
        name = w.title
        w.close()
        logger.log("close_window", {"title": title}, f"Closed: {name}")
        return f"✅ Closed window: {name}"
    except Exception as e:
        msg = f"❌ Error closing window: {e}"
        logger.log("close_window", {"title": title}, msg, status="error")
        return msg
