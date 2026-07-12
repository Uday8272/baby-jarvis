"""
system_tools — Gives Jarvis full control over the host PC.

Every public function in the sub-modules is decorated with @tool so it
can be bound directly to a LangChain/LangGraph agent.
"""

from system_tools.shell import run_shell_command, run_powershell
from system_tools.file_ops import (
    read_file,
    write_file,
    list_directory,
    move_path,
    delete_path,
    search_files,
    get_file_info,
)
from system_tools.app_launcher import open_application, open_url, close_application
from system_tools.screen import take_screenshot
from system_tools.keyboard_mouse import type_text, press_hotkey, click_at, move_mouse
from system_tools.clipboard import get_clipboard, set_clipboard
from system_tools.system_info import (
    get_system_stats,
    list_processes,
    get_network_info,
    kill_process,
)
from system_tools.window_mgmt import (
    list_windows,
    focus_window,
    minimize_window,
    maximize_window,
    close_window,
)
from system_tools.volume import set_volume, get_volume, toggle_mute
from system_tools.rag_tool import search_local_files, ingest_local_folder
from system_tools.safety import ActionLogger

# Convenient list of every tool for binding to the agent
ALL_TOOLS = [
    # Shell
    run_shell_command,
    run_powershell,
    # Files
    read_file,
    write_file,
    list_directory,
    move_path,
    delete_path,
    search_files,
    get_file_info,
    # Apps
    open_application,
    open_url,
    close_application,
    # Screen
    take_screenshot,
    # Keyboard & Mouse
    type_text,
    press_hotkey,
    click_at,
    move_mouse,
    # Clipboard
    get_clipboard,
    set_clipboard,
    # System Info
    get_system_stats,
    list_processes,
    get_network_info,
    kill_process,
    # Window Management
    list_windows,
    focus_window,
    minimize_window,
    maximize_window,
    close_window,
    # Volume
    set_volume,
    get_volume,
    toggle_mute,
    # RAG — Local Document Search
    search_local_files,
    ingest_local_folder,
]
