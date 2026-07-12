"""
shell.py — Execute shell commands on the host machine.
"""

import subprocess

from langchain_core.tools import tool

from system_tools.safety import is_command_blocked, logger


@tool
def run_shell_command(command: str, timeout: int = 30) -> str:
    """
    Execute a shell command via CMD and return stdout + stderr.

    Use this for general-purpose command execution like listing files,
    checking system status, running scripts, git commands, etc.

    Args:
        command: The command string to execute (e.g. "dir C:\\Users")
        timeout: Maximum seconds to wait before killing the process (default 30)
    """
    if is_command_blocked(command):
        logger.log("run_shell_command", {"command": command}, "BLOCKED", status="blocked")
        return f"⛔ BLOCKED: This command matches a safety blocklist pattern and cannot be executed: {command}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=None,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr}"
        if result.returncode != 0:
            output += f"\n[EXIT CODE]: {result.returncode}"

        response = output.strip() or "(command produced no output)"
        logger.log("run_shell_command", {"command": command}, response)
        return response

    except subprocess.TimeoutExpired:
        msg = f"⏰ Command timed out after {timeout} seconds: {command}"
        logger.log("run_shell_command", {"command": command}, msg, status="error")
        return msg
    except Exception as e:
        msg = f"❌ Error executing command: {e}"
        logger.log("run_shell_command", {"command": command}, msg, status="error")
        return msg


@tool
def run_powershell(script: str, timeout: int = 30) -> str:
    """
    Execute a PowerShell script/command and return the output.

    Use this when you need PowerShell-specific features like cmdlets,
    piping, or advanced Windows administration.

    Args:
        script: The PowerShell command or script to execute
        timeout: Maximum seconds to wait (default 30)
    """
    if is_command_blocked(script):
        logger.log("run_powershell", {"script": script}, "BLOCKED", status="blocked")
        return f"⛔ BLOCKED: This script matches a safety blocklist pattern."

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr}"
        if result.returncode != 0:
            output += f"\n[EXIT CODE]: {result.returncode}"

        response = output.strip() or "(command produced no output)"
        logger.log("run_powershell", {"script": script}, response)
        return response

    except subprocess.TimeoutExpired:
        msg = f"⏰ PowerShell script timed out after {timeout} seconds."
        logger.log("run_powershell", {"script": script}, msg, status="error")
        return msg
    except Exception as e:
        msg = f"❌ Error executing PowerShell: {e}"
        logger.log("run_powershell", {"script": script}, msg, status="error")
        return msg
