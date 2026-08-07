"""
system_tools — Gives Jarvis full control over the host PC.

Every public function in the sub-modules is decorated with @tool so it
can be bound directly to a LangChain/LangGraph agent.
"""

from agent.tools.shell import run_shell_command, run_powershell
from agent.tools.file_ops import (
    read_file,
    write_file,
    list_directory,
    move_path,
    delete_path,
    search_files,
    get_file_info,
)
from agent.tools.app_launcher import open_application, open_url, close_application
from agent.tools.screen import take_screenshot
from agent.tools.keyboard_mouse import type_text, press_hotkey, click_at, move_mouse
from agent.tools.clipboard import get_clipboard, set_clipboard
from agent.tools.system_info import (
    get_system_stats,
    list_processes,
    get_network_info,
    kill_process,
)
from agent.tools.window_mgmt import (
    list_windows,
    focus_window,
    minimize_window,
    maximize_window,
    close_window,
)
from agent.tools.volume import set_volume, get_volume, toggle_mute
from agent.tools.rag_tool import search_local_files, ingest_local_folder
from agent.tools.web_scraper import scrape_webpage, scrape_dynamic_page
from agent.scheduler import SCHEDULER_TOOLS
from agent.tools.safety import ActionLogger

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
    # web scraping 
    scrape_webpage, 
    scrape_dynamic_page, 
    # scheduler and routines 
    *SCHEDULER_TOOLS, 
]
