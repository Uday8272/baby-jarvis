"""
app_launcher.py — Open and close applications, open URLs.
"""

import os
import subprocess
import webbrowser

from langchain_core.tools import tool

from agent.tools.safety import logger


@tool
def open_application(name_or_path: str) -> str:
    """
    Open an application by name or full path.
    Common names: notepad, calc, mspaint, explorer, code, chrome, cmd, powershell,
    taskmgr, control, regedit, mstsc, snippingtool, winver, devmgmt.msc

    Args:
        name_or_path: Application name (e.g. "notepad") or full path (e.g. "C:\\Program Files\\app.exe")
    """
    try:
        # If it looks like a path, use os.startfile
        if os.path.sep in name_or_path or name_or_path.endswith(".exe"):
            os.startfile(name_or_path)
        else:
            # Try common aliases first
            subprocess.Popen(
                name_or_path,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        logger.log("open_application", {"name_or_path": name_or_path}, "Launched successfully")
        return f"✅ Launched: {name_or_path}"
    except Exception as e:
        msg = f"❌ Failed to open application: {e}"
        logger.log("open_application", {"name_or_path": name_or_path}, msg, status="error")
        return msg


@tool
def open_url(url: str) -> str:
    """
    Open a URL in the user's default web browser.

    Args:
        url: The URL to open (e.g. "https://google.com")
    """
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        logger.log("open_url", {"url": url}, "Opened in browser")
        return f"✅ Opened in browser: {url}"
    except Exception as e:
        msg = f"❌ Failed to open URL: {e}"
        logger.log("open_url", {"url": url}, msg, status="error")
        return msg


@tool
def close_application(process_name: str) -> str:
    """
    Close/kill an application by its process name.

    Args:
        process_name: Process name (e.g. "notepad.exe", "chrome.exe").
                      The .exe extension is optional.
    """
    try:
        if not process_name.endswith(".exe"):
            process_name += ".exe"

        result = subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout.strip() or result.stderr.strip()
        logger.log("close_application", {"process_name": process_name}, output)
        return f"✅ {output}" if result.returncode == 0 else f"⚠️ {output}"
    except Exception as e:
        msg = f"❌ Failed to close application: {e}"
        logger.log("close_application", {"process_name": process_name}, msg, status="error")
        return msg
