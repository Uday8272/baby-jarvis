
"""
watcher.py — File system watcher for Jarvis.
Uses the Watchdog library to monitor directories for file changes.
When events occur (file created, modified, deleted), the watcher
logs them and can optionally trigger Jarvis actions.
""" 

import os 
import time 
from pathlib import Path 

from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler, FileCreatedEvent 

# active watches registry 
# maps watched paths to their observer instances 

_watchers: dict[str, Observer] = {} 
_event_logs: list[dict] = []  # in memory log of recent events 

class jarvis_file_handler(FileSystemEventHandler):
    '''
    custom event handler that logs file system changes
    ''' 

    def __init__(self, watch_path: str):
        super().__init__()
        self.watch_path = watch_path 

# creation -------------------------------------------------------
    def on_created(self, event):
        if not event.is_directory:
            entry = {
                "event": 'created', 
                'path': event.src_path, 
                'watch_path': self.watch_path, 
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            } 
            _event_logs.append(entry) 
            print(f'[WATCHER] new file: {event.src_path}')

# modification -------------------------------------------------------
    def on_modified(self, event):
        if not event.is_directory:
            entry = {
                'event': 'modified', 
                'path': event.src_path, 
                'watch_path': self.watch_path, 
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            _event_logs.append(entry)
            print(f'[WATCHER] modified file: {event.src_path}')

# deletion -------------------------------------------------------
    def on_deleted(self, event):
        if not event.is_directory:
            entry = {
                'event': 'deleted',
                'path': event.src_path, 
                'watch_path': self.watch_path, 
                'time': time.strftime("%Y-%m-%d %H:%M:%S"),
            } 
            _event_logs.append(entry) 
            print(f'[WATCHER] file deleted: {event.src_path}') 

# moving -------------------------------------------------------
    def on_moved(self, event):
        if not event.is_directory:
            entry = {
                'event': 'moved', 
                'path': event.src_path, 
                'destination': event.dest_path, 
                'watch_path': self.watch_path, 
                'time': time.strftime("%Y-%m-%d %H:%M:%S"), 
            } 

            _event_logs.append(entry)
            print(f"[WACTHER] file moved: {event.src_path} -> {event.dest_path}")

# public api ---------------------------------------------------------
def start_watching(folder_path: str, recursive: bool = True) -> str: 

    """
    Start watching a folder for file changes.
    Args:
        folder_path: Absolute path to the folder to watch.
        recursive: Whether to watch subdirectories too.
    Returns:
        Confirmation string.
    """ 

    # normalize the path ---------------------
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return f"Error: '{folder_path}' is not a valid directory."
    if folder_path in _watchers:
        return f"Already watching '{folder_path}'."
    handler = jarvis_file_handler(folder_path)
    observer = Observer()
    observer.schedule(handler, folder_path, recursive=recursive)
    observer.start()
    _watchers[folder_path] = observer
    print(f"[WATCHER] 👁️ Started watching: {folder_path}")
    return f"Now watching '{folder_path}' for file changes." 

# function : stop_watching --------------------------------------
def stop_watching(folder_path: str) -> str:
    """
    Stop watching a folder.
    Args:
        folder_path: The folder path to stop watching.
    Returns:
        Confirmation string.
    """
    folder_path = os.path.abspath(folder_path)
    if folder_path not in _watchers:
        return f"Not currently watching '{folder_path}'."
    observer = _watchers.pop(folder_path)
    observer.stop()
    observer.join(timeout=5)
    print(f"[WATCHER] 🛑 Stopped watching: {folder_path}")
    return f"Stopped watching '{folder_path}'."
    
# function : list the watches ------------------------------------
    '''
    return the last N file system events accross all watches
    ''' 
def list_watches() -> list[str]: 
    return list(_watchers.keys())


# function : get the recent event --------------------------------------
def get_recent_events(n: int = 20) -> list[dict]:
    """Return the last N file system events across all watchers."""
    return _event_logs[-n:]


# stop all the watchers ---------------------------------------
def stop_all_watchers() -> None:
    """Stop all active watchers. Called during server shutdown."""
    for path, observer in _watchers.items():
        observer.stop()
        observer.join(timeout=5)
        print(f"[WATCHER] Stopped watching: {path}")
    _watchers.clear() 

    
    