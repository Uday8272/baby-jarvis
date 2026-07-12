"""
Entry point for Baby Jarvis on Windows.

Forces uvicorn to use SelectorEventLoop (required by psycopg async driver).
Sets the Windows event loop policy before starting uvicorn so that all
async I/O uses SelectorEventLoop instead of the default ProactorEventLoop.
"""

import asyncio
import sys

import uvicorn

if __name__ == "__main__":
    # psycopg async requires SelectorEventLoop on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
    )
