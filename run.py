"""
Entry point for Baby Jarvis on Windows.

Forces uvicorn to use SelectorEventLoop (required by psycopg async driver).
Sets the Windows event loop policy before starting uvicorn so that all
async I/O uses SelectorEventLoop instead of the default ProactorEventLoop.
"""

import asyncio
import sys

import uvicorn

# Default ProactorEventLoop is fine and required for Playwright subprocesses
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
