"""
file_ops.py — File system operations.
"""

import glob
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.tools import tool

from agent.tools.safety import logger


@tool
def read_file(path: str) -> str:
    """
    Read and return the contents of a text file.

    Args:
        path: Absolute or relative path to the file to read
    """
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"❌ File not found: {p}"
        if not p.is_file():
            return f"❌ Path is not a file: {p}"
        if p.stat().st_size > 5 * 1024 * 1024:  # 5 MB limit
            return f"⚠️ File is too large to read ({p.stat().st_size:,} bytes). Use a shell command instead."

        content = p.read_text(encoding="utf-8", errors="replace")
        logger.log("read_file", {"path": str(p)}, f"Read {len(content)} chars")
        return content
    except Exception as e:
        msg = f"❌ Error reading file: {e}"
        logger.log("read_file", {"path": path}, msg, status="error")
        return msg


@tool
def write_file(path: str, content: str) -> str:
    """
    Write content to a file. Creates the file and parent directories if they
    don't exist. Overwrites if the file already exists.

    Args:
        path: Absolute or relative path to the file to write
        content: The text content to write into the file
    """
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.log("write_file", {"path": str(p)}, f"Wrote {len(content)} chars")
        return f"✅ File written successfully: {p} ({len(content)} characters)"
    except Exception as e:
        msg = f"❌ Error writing file: {e}"
        logger.log("write_file", {"path": path}, msg, status="error")
        return msg


@tool
def list_directory(path: str = ".") -> str:
    """
    List the contents of a directory with file sizes and types.

    Args:
        path: Directory path to list (defaults to current directory)
    """
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"❌ Directory not found: {p}"
        if not p.is_dir():
            return f"❌ Path is not a directory: {p}"

        entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = [f"📂 Contents of: {p}\n"]
        for entry in entries:
            if entry.is_dir():
                count = sum(1 for _ in entry.iterdir()) if entry.exists() else 0
                lines.append(f"  📁 {entry.name}/  ({count} items)")
            else:
                size = entry.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                lines.append(f"  📄 {entry.name}  ({size_str})")

        result = "\n".join(lines) if len(entries) > 0 else f"📂 {p} is empty."
        logger.log("list_directory", {"path": str(p)}, f"{len(entries)} entries")
        return result
    except Exception as e:
        msg = f"❌ Error listing directory: {e}"
        logger.log("list_directory", {"path": path}, msg, status="error")
        return msg


@tool
def move_path(source: str, destination: str) -> str:
    """
    Move or rename a file or directory.

    Args:
        source: Path to the file or directory to move
        destination: Destination path
    """
    try:
        src = Path(source).resolve()
        dst = Path(destination).resolve()
        if not src.exists():
            return f"❌ Source not found: {src}"
        shutil.move(str(src), str(dst))
        logger.log("move_path", {"source": str(src), "destination": str(dst)}, "Moved successfully")
        return f"✅ Moved: {src} → {dst}"
    except Exception as e:
        msg = f"❌ Error moving: {e}"
        logger.log("move_path", {"source": source, "destination": destination}, msg, status="error")
        return msg


@tool
def delete_path(path: str) -> str:
    """
    Delete a file or directory. Directories are deleted recursively.
    Use with caution.

    Args:
        path: Path to the file or directory to delete
    """
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"❌ Path not found: {p}"

        if p.is_file():
            p.unlink()
            logger.log("delete_path", {"path": str(p)}, "File deleted")
            return f"✅ Deleted file: {p}"
        elif p.is_dir():
            shutil.rmtree(str(p))
            logger.log("delete_path", {"path": str(p)}, "Directory deleted")
            return f"✅ Deleted directory: {p}"
        else:
            return f"❌ Unknown path type: {p}"
    except Exception as e:
        msg = f"❌ Error deleting: {e}"
        logger.log("delete_path", {"path": path}, msg, status="error")
        return msg


@tool
def search_files(directory: str, pattern: str) -> str:
    """
    Search for files matching a glob pattern within a directory.

    Args:
        directory: Root directory to search in
        pattern: Glob pattern (e.g. "*.py", "**/*.txt", "report*")
    """
    try:
        p = Path(directory).resolve()
        if not p.exists():
            return f"❌ Directory not found: {p}"

        matches = list(p.glob(pattern))
        if not matches:
            return f"No files found matching '{pattern}' in {p}"

        lines = [f"🔍 Found {len(matches)} matches for '{pattern}' in {p}:\n"]
        for m in matches[:50]:  # limit to 50 results
            rel = m.relative_to(p)
            kind = "📁" if m.is_dir() else "📄"
            lines.append(f"  {kind} {rel}")
        if len(matches) > 50:
            lines.append(f"\n  ... and {len(matches) - 50} more")

        result = "\n".join(lines)
        logger.log("search_files", {"directory": str(p), "pattern": pattern}, f"{len(matches)} matches")
        return result
    except Exception as e:
        msg = f"❌ Error searching: {e}"
        logger.log("search_files", {"directory": directory, "pattern": pattern}, msg, status="error")
        return msg


@tool
def get_file_info(path: str) -> str:
    """
    Get detailed information about a file or directory (size, dates, type).

    Args:
        path: Path to the file or directory
    """
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"❌ Path not found: {p}"

        stat = p.stat()
        info = {
            "path": str(p),
            "type": "directory" if p.is_dir() else "file",
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "extension": p.suffix if p.is_file() else "N/A",
        }

        lines = [f"ℹ️ File Info: {p}"]
        for k, v in info.items():
            lines.append(f"  {k}: {v}")

        result = "\n".join(lines)
        logger.log("get_file_info", {"path": str(p)}, result)
        return result
    except Exception as e:
        msg = f"❌ Error getting file info: {e}"
        logger.log("get_file_info", {"path": path}, msg, status="error")
        return msg
