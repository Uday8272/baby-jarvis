"""
Safety layer — action logging, blocklist, and confirmation mode.

Every system tool call goes through the ActionLogger so there is a full
audit trail of everything Jarvis does on the machine.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# ── Blocklist ────────────────────────────────────────────────────────────────
# Patterns that will be REFUSED outright regardless of confirmation mode.

BLOCKED_COMMAND_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),       # format C:
    re.compile(r"\brm\s+-rf\s+/\s*$", re.IGNORECASE),         # rm -rf /
    re.compile(r"\bdel\s+/[sf]\s+[a-zA-Z]:\\", re.IGNORECASE),# del /s /f C:\
    re.compile(r"\brd\s+/[sq]\s+[a-zA-Z]:\\", re.IGNORECASE), # rd /s /q C:\
    re.compile(r"\bshutdown\s+/[sp]", re.IGNORECASE),         # shutdown /s, /p
    re.compile(r"Remove-Item\s+.*-Recurse.*-Force.*[A-Z]:\\$", re.IGNORECASE),
    re.compile(r"\breg\s+delete\s+HKLM", re.IGNORECASE),      # registry nuke
    re.compile(r"\bbcdedit", re.IGNORECASE),                   # boot config
    re.compile(r"\bdiskpart", re.IGNORECASE),                  # disk partition
]

# Patterns that require confirmation in "dangerous-only" mode
DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bdel\b|\bremove\b|\brmdir\b|\brd\b", re.IGNORECASE),
    re.compile(r"\btaskkill\b|\bStop-Process\b", re.IGNORECASE),
    re.compile(r"\bnet\s+stop\b|\bsc\s+stop\b", re.IGNORECASE),
    re.compile(r"\breg\s+(add|delete)\b", re.IGNORECASE),
    re.compile(r"Remove-Item", re.IGNORECASE),
]


def is_command_blocked(command: str) -> bool:
    """Return True if the command matches a hard-blocked pattern."""
    return any(pattern.search(command) for pattern in BLOCKED_COMMAND_PATTERNS)


def is_command_dangerous(command: str) -> bool:
    """Return True if the command matches a dangerous pattern (needs confirmation)."""
    return any(pattern.search(command) for pattern in DANGEROUS_PATTERNS)


# ── Action Logger ────────────────────────────────────────────────────────────

from backend.config import get_settings
settings = get_settings()
LOG_DIR = Path(settings.jarvis_log_dir)


class ActionLogger:
    """
    Writes a JSON-lines log of every system action Jarvis performs.

    Each entry contains:
        - timestamp (ISO-8601 UTC)
        - tool_name
        - arguments (dict)
        - result_summary (first 500 chars of output)
        - status ("ok" | "error" | "blocked")
    """

    def __init__(self, log_dir: Path = LOG_DIR) -> None:
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._log_path = self._log_dir / f"actions_{today}.jsonl"

    def log(
        self,
        tool_name: str,
        arguments: dict,
        result: str,
        status: str = "ok",
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "args": arguments,
            "result_summary": result[:500],
            "status": status,
        }
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_recent(self, n: int = 20) -> list[dict]:
        """Return the last *n* log entries."""
        if not self._log_path.exists():
            return []
        with open(self._log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-n:]]


# Module-level singleton so every tool can share one logger
logger = ActionLogger()
