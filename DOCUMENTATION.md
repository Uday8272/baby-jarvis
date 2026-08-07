# JARVIS — Technical Documentation

> **Living Document** — Updated as the project evolves. Last updated: August 2026.

---

## 1. Project Overview

JARVIS is a personal AI assistant with full control over a Windows PC. It is built as a local, self-hosted web application that you interact with through a browser-based chat UI. At its core, it uses Google Gemini (via LangGraph's ReAct agent loop) to understand natural language commands and execute them autonomously using a rich library of system tools.

**Key design principles:**
- **Local-first**: Runs entirely on your own machine. No data leaves unless you use a cloud model API.
- **Agent-based**: The LLM is not just a chatbot — it is a ReAct agent that reasons, decides which tool to use, executes it, and reflects on the result in a loop until the task is complete.
- **Persistent memory**: Conversations are saved to a Postgres (Supabase) database, so Jarvis remembers what you talked about across restarts.
- **Extensible**: New capabilities (tools, schedulers, watchers) are plug-and-play.

---

## 2. High-Level Architecture

```
Browser (frontend/)
    |
    |  HTTP (JWT-authenticated)
    v
backend/main.py  <-- FastAPI application (single server)
    |
    |-- /auth/token       -> JWT login
    |-- /chat             -> Authenticated chat (with SQL history)
    |-- /api/chat         -> Unauthenticated alias (for local UI)
    |-- /api/actions/log  -> View Jarvis action log
    +-- /ui               -> Serves the frontend HTML
    |
    v
agent/graph.py  <-- LangGraph ReAct Agent
    |
    |-- agent/tools/      -> System tools (shell, files, apps, etc.)
    +-- agent/scheduler/  -> Task scheduler & folder watcher tools
    |
    v
backend/config.py  <-- Centralized environment config (.env)
    |
    |-- Supabase Postgres  -> Persistent conversation checkpointing
    +-- SQLite (fallback)  -> In-memory or local DB
```

---

## 3. Directory Structure

```
jarvis/
|
|-- run.py                   # App entrypoint -- runs uvicorn
|
|-- frontend/                # Web UI
|   |-- index.html           # HTML structure
|   |-- style.css            # All CSS styles
|   +-- app.js               # All JavaScript (auth, chat, voice)
|
|-- backend/                 # FastAPI server & auth
|   |-- main.py              # * Single server entrypoint, all API routes
|   |-- config.py            # * Centralized .env config (get_settings())
|   |-- security.py          # JWT token creation & validation
|   |-- db.py                # SQLModel database engine setup
|   |-- crud/                # DB operations (users, sessions, messages)
|   |-- models/              # SQLModel table definitions
|   +-- services/            # LLM service (legacy, bypassed by agent)
|
|-- agent/                   # AI Agent core
|   |-- graph.py             # * LangGraph ReAct agent definition & system prompt
|   |-- tools/               # All system tools (LangChain @tool functions)
|   |   |-- __init__.py      # Exports ALL_TOOLS list
|   |   |-- shell.py         # Run shell & PowerShell commands
|   |   |-- file_ops.py      # Read, write, move, delete files
|   |   |-- app_launcher.py  # Open/close apps, open URLs
|   |   |-- screen.py        # Take screenshots
|   |   |-- keyboard_mouse.py# Type text, hotkeys, mouse control
|   |   |-- clipboard.py     # Get/set clipboard
|   |   |-- system_info.py   # CPU, RAM, processes, network
|   |   |-- window_mgmt.py   # List, focus, minimize, maximize windows
|   |   |-- volume.py        # Control system volume
|   |   |-- web_scraper.py   # Read and extract content from websites (static & dynamic)
|   |   |-- rag_tool.py      # Search & ingest local documents (RAG)
|   |   +-- safety.py        # Action logger (audit trail)
|   +-- scheduler/           # Background task scheduling
|       |-- __init__.py      # Exports SCHEDULER_TOOLS list
|       |-- engine.py        # APScheduler wrapper (SQLite persistence)
|       |-- tools.py         # LangChain tools for scheduling
|       |-- jobs.py          # Job execution bridge -> invokes agent
|       +-- watcher.py       # Watchdog folder monitoring
|
|-- voice/                   # Voice daemon (background listener)
|   +-- daemon.py            # Vosk-powered offline wake-word detector ("Jarvis")
|-- rag/                     # RAG (document ingestion) utilities
|-- data/                    # Runtime data (logs, screenshots, scheduler DB)
+-- .env                     # * All secret keys and configuration
```

---

## 4. Component Deep Dives

### 4.1 `run.py` — Entrypoint
Starts the uvicorn server pointing at `backend.main:app`. Sets the Windows event loop policy for compatibility with async libraries.

### 4.2 `backend/main.py` — The Single Server
This is the heart of the application. It was created by merging the original `agent/server.py` and `backend/main.py` into one file.

**Startup (lifespan):**
1. Initialises the SQL database (`init_db()`).
2. Attempts a Postgres connection via `DATABASE_URL`. Falls back to `MemorySaver` if unavailable.
3. Compiles the LangGraph agent with the checkpointer.
4. Starts the APScheduler background task scheduler.
5. Starts Watchdog folder watchers.

**Key endpoints:**

| Endpoint | Auth | Description |
|---|---|---|
| `POST /auth/token` | None | OAuth2 login. Returns a JWT. |
| `GET /auth/whoami` | JWT | Returns the logged-in username. |
| `POST /chat` | JWT | Main authenticated chat with SQL history tracking. |
| `POST /api/chat` | None | Unauthenticated alias used by the local web UI. |
| `GET /api/actions/log` | None | Returns Jarvis's recent action log. |
| `GET /ui` | None | Serves `frontend/index.html`. |
| `GET /frontend/*` | None | Serves static CSS/JS files. |

### 4.3 `backend/config.py` — Centralized Configuration
All environment variables are read **once** here via `get_settings()` which returns a frozen `Settings` dataclass. Every other module imports from here instead of calling `os.getenv()` directly.

**Required `.env` variables:**
```
JWT_SECRET_KEY               # Long random hex string (secrets.token_hex(32))
JARVIS_OWNER_USERNAME        # Your login username
JARVIS_OWNER_PASSWORD_HASH   # bcrypt hash of your password
GEMINI_API_KEY               # Your Google Gemini API key
DATABASE_URL                 # PostgreSQL connection string (Supabase)
TAVILY_API_KEY               # For web search tool
```

### 4.4 `agent/graph.py` — The ReAct Agent
Defines the LangGraph `StateGraph` with a `MessagesState`. The agent node uses `ChatGoogleGenerativeAI` (Gemini) bound to all tools in `ALL_TOOLS`. It loops: **Reason -> Tool Call -> Observe -> Reason** until it produces a final answer.

The **System Prompt** lives here. It tells Jarvis who it is, what tools it has, and how to behave (e.g., prefer PowerShell, be decisive, always speak in first person).

### 4.5 `agent/tools/` — System Control Tools
Each file exposes one or more LangChain `@tool`-decorated functions. They are all imported and assembled into the `ALL_TOOLS` list in `__init__.py`, which is then bound to the agent.

**Action Logger** (`safety.py`): Every sensitive action is automatically logged to `data/logs/` with a timestamp. Viewable via `/api/actions/log`.

### 4.6 `agent/scheduler/` — Background Task Scheduling
Built on top of **APScheduler** with SQLite persistence (`data/scheduler.db`), so scheduled jobs survive server restarts.

- **`engine.py`**: Singleton scheduler. Exposes `add_one_shot_task`, `add_cron_task`, `get_all_tasks`, `remove_task`.
- **`tools.py`**: Wraps the engine functions as LangChain tools so the agent can schedule tasks in natural language.
- **`jobs.py`**: When a job fires, it calls `execute_scheduled_task()`, which invokes the full LangGraph agent and speaks the response via TTS.
- **`watcher.py`**: Uses **Watchdog** to monitor filesystem directories. When a change is detected, it invokes the agent to announce it.

### 4.7 `frontend/` — Web UI
A single-page app with no build step. Pure HTML/CSS/JS.

**Authentication flow:**
1. On page load, `app.js` checks `localStorage` for a saved JWT (`jarvis_token`).
2. If no token, the login overlay is shown (full-screen, above everything).
3. On form submit, `fetch('/auth/token')` is called with `application/x-www-form-urlencoded` credentials.
4. On success, the JWT is saved to `localStorage` and the overlay fades out.
5. Every subsequent `/api/chat` call includes `Authorization: Bearer <token>`.
6. If a `401` is received, the token is cleared and the login overlay is shown again.

---

## 5. Data Flow — A Single Chat Message

```
User types "Open Spotify" -> presses Enter
    |
    v
app.js: sendMessage()
    -> GET token from localStorage
    -> POST /api/chat  { query: "Open Spotify", session_id: "abc123" }
          Authorization: Bearer <jwt>
    |
    v
backend/main.py: run_chat()
    -> agent_app.invoke({ messages: [HumanMessage("Open Spotify")] })
    |
    v
agent/graph.py: ReAct loop
    -> Reason: "I should use open_application tool"
    -> Tool call: open_application(name="Spotify")
    |
    v
agent/tools/app_launcher.py: open_application()
    -> subprocess.Popen(["start", "spotify"])
    -> Returns "Opened Spotify"
    |
    v
agent/graph.py: ReAct loop
    -> Observe tool result
    -> Reason: "Task complete"
    -> Final response: "Spotify is now open!"
    |
    v
backend/main.py: returns { result: "Spotify is now open!", session_id: "abc123" }
    |
    v
app.js: addMessage('jarvis', "Spotify is now open!")
    -> Renders in chat
    -> speakText() -> Web Speech API reads it aloud
```

---

## 6. Development Guide

### Running the server
```powershell
# Activate virtual environment
.venv\Scripts\activate

# Start Jarvis
python run.py
```
Then open: `http://127.0.0.1:8000/ui`

### Adding a new tool
1. Create a new file in `agent/tools/` (e.g., `agent/tools/calendar.py`).
2. Define a function decorated with `@tool`.
3. Import it in `agent/tools/__init__.py` and add it to the `ALL_TOOLS` list.
4. Update the system prompt in `agent/graph.py` to mention the new capability.

### Adding a new API endpoint
Add it to `backend/main.py`. If it needs authentication, add `_owner: str = Depends(get_current_owner)` as a parameter.

---

## 7. Key Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web framework & API server |
| `uvicorn` | ASGI server |
| `langchain` / `langgraph` | Agent framework & ReAct loop |
| `langchain-google-genai` | Gemini model integration |
| `langchain-tavily` | Web search tool |
| `apscheduler` | Background task scheduling |
| `watchdog` | Filesystem change monitoring |
| `beautifulsoup4` / `httpx` | Static web scraping |
| `playwright` | Dynamic web scraping (JavaScript rendering) |
| `psycopg` | Postgres driver for conversation memory |
| `sqlmodel` | SQL ORM for chat history database |
| `python-jose` / `bcrypt` | JWT authentication & password hashing |
| `pyttsx3` | Text-to-speech for scheduled task notifications & Voice Mode |
| `vosk` / `sounddevice` | Offline background wake-word detection ("Hey Jarvis") |
| `chromadb` | Vector store for RAG (local document search) |

---

## 8. Change Log

| Date | Change | Phase |
|---|---|---|
| Early 2026 | Initial project -- basic FastAPI + raw LLM chat | Phase 1 |
| July 2026 | Integrated LangGraph ReAct agent with system tools | Phase 5-9 |
| July 22, 2026 | Added Task Scheduler (APScheduler + voice notifications) | Phase 10 |
| July 28, 2026 | Pushed task scheduler to GitHub (refactor/organize-features) | Phase 10 |
| July 30, 2026 | Architectural cleanup: merged servers, reorganized agent/tools/ & agent/scheduler/ | Phase 11 |
| July 30, 2026 | Centralized all config in backend/config.py | Phase 11 |
| August 7, 2026 | Added JWT login screen to frontend | Phase 12 |
| August 7, 2026 | Split index.html into index.html + style.css + app.js | Phase 12 |
| August 7, 2026 | Added Web Scraping tools (BeautifulSoup + Playwright) | Phase 13 |
| August 8, 2026 | Added offline Voice Mode background daemon (Vosk) | Phase 14 |
