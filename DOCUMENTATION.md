# JARVIS Project Documentation

Welcome to the JARVIS project documentation. This document serves as a comprehensive guide to understanding the architecture, features, and setup of the JARVIS project. 

As the project evolves, this document will be updated to reflect the latest changes and additions.

---

## 1. Project Overview

The JARVIS project is divided into these major components:
1. **Backend API (`backend/`)**: A secure, single-owner FastAPI backend that handles JWT authentication, conversation memory with SQLModel, and multi-provider LLM integration.
2. **Jarvis ReAct Agent (`agent/`)**: A LangGraph-powered ReAct agent with full PC system control — shell commands, file management, app launching, screenshots, keyboard/mouse, clipboard, system monitoring, window management, volume control, and web search. All through natural language.
3. **System Tools (`system_tools/`)**: A modular Python package of LangChain-compatible tools that give Jarvis the ability to interact with every aspect of the Windows operating system.
4. **Voice / Daemon (`voice/`)**: 24/7 voice-activated background daemon with wake-word detection and TTS responses.
5. **RAG Engine (`rag/`)**: Local document search and indexing using ChromaDB and HuggingFace embeddings.
6. **Frontend (`frontend/`)**: Premium dark-mode chat web interface.
7. **Legacy Pipeline (`legacy/`)**: The original multi-agent research pipeline preserved for backward compatibility.

---

## 2. Project Structure

```
jarvis/
├── backend/                  ← Core API (auth, chat, LLM service)
│   ├── config.py, db.py, security.py, main.py
│   ├── crud/chat.py
│   ├── models/entities.py
│   └── services/llm.py, conversation.py
├── agent/                    ← ReAct Agent + Server
│   ├── graph.py              ← Agent graph definition
│   └── server.py             ← FastAPI server (serves agent + UI)
├── system_tools/             ← System control tools
├── voice/                    ← Voice daemon
│   ├── daemon.py
│   └── start_daemon.bat
├── rag/                      ← RAG / Document search engine
│   ├── engine.py
│   └── test_engine.py
├── legacy/                   ← Legacy research pipeline
│   └── pipeline.py
├── frontend/                 ← Web UI
│   └── index.html
├── data/                     ← Runtime data (gitignored)
│   ├── chroma_db/
│   ├── logs/
│   └── screenshots/
├── scripts/                  ← Utility scripts
├── run.py                    ← Entry point
└── .env / .env.example
```

---

## 3. Backend API (`backend/`)

The Backend API is a FastAPI-based backend that exposes authenticated chat endpoints. It uses an abstracted layer for LLM integrations, allowing swapping between models like Gemini, OpenAI, Anthropic, Groq, and Ollama.

### 3.1 Architecture
* **Framework**: FastAPI
* **Database**: SQLite (default) / PostgreSQL (Supabase ready). Models are built using SQLModel.
* **Authentication**: OAuth2 Password Flow with JWT (JSON Web Tokens). Only a single "owner" can access the system.
* **LLM Layer**: Protocol-based abstraction (`backend/services/llm.py`).

### 3.2 Core Files and Directories
* `backend/main.py`: The entry point for the FastAPI server, defining all routes (`/chat`, `/auth/token`, etc.).
* `backend/config.py`: Environment configuration management using `dataclasses`. Reads from `.env`.
* `backend/db.py`: Database connection and session management.
* `backend/security.py`: JWT token creation, password hashing, and owner authentication logic.
* `backend/models/entities.py`: SQLModel table definitions (`User`, `ChatSession`, `Message`).
* `backend/crud/chat.py`: Database operations (Create, Read, Update) for chat memory.
* `backend/services/llm.py`: Provider-agnostic LLM interface and Gemini implementation.
* `backend/services/conversation.py`: Helper functions to construct prompts using chat history.

### 3.3 Setup and Running

1. **Environment Setup**:
   Create a `.env` file (you can copy `.env.example`).
   Required variables include:
   - `JWT_SECRET_KEY`
   - `JARVIS_OWNER_USERNAME`
   - `JARVIS_OWNER_PASSWORD_HASH` (Generated using `scripts/generate_password_hash.py`)
   - `LLM_PROVIDER` (e.g., `gemini`)
   - `GEMINI_API_KEY` (or other provider keys)

2. **Start the API**:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

3. **Usage**:
   - Get a token by sending a POST request to `/auth/token` with your username and password.
   - Use the token as a Bearer token to access `/chat`, `/chat/sessions`, and `/chat/sessions/{session_id}/messages`.

---

## 4. Jarvis ReAct Agent (`agent/`)

The ReAct Agent is the primary Jarvis interface — a flexible, tool-calling AI that can control your entire PC through natural language.

### 4.1 Architecture (LangGraph ReAct)

Unlike the old fixed pipeline, the ReAct agent uses a **flexible tool-calling loop**:

```
User Message → LLM (Gemini 2.5 Flash + all tools) → Tool Call?
    → YES: Execute tool → Feed result back → Loop
    → NO: Return final response
```

* **Model**: Gemini 2.5 Flash with function calling
* **State Persistence**: PostgresSaver backed by Supabase Postgres
* **Tool Binding**: All system tools + Tavily web search are bound as LangChain tools

### 4.2 System Tools (`system_tools/`)

| Module | Tools | Description |
|---|---|---|
| `shell.py` | `run_shell_command`, `run_powershell` | Execute CMD/PowerShell commands |
| `file_ops.py` | `read_file`, `write_file`, `list_directory`, `move_path`, `delete_path`, `search_files`, `get_file_info` | Full file system control |
| `app_launcher.py` | `open_application`, `open_url`, `close_application` | Launch/close apps, open URLs |
| `screen.py` | `take_screenshot` | Capture screen to PNG |
| `keyboard_mouse.py` | `type_text`, `press_hotkey`, `click_at`, `move_mouse` | Keyboard & mouse automation |
| `clipboard.py` | `get_clipboard`, `set_clipboard` | Clipboard read/write |
| `system_info.py` | `get_system_stats`, `list_processes`, `get_network_info`, `kill_process` | System monitoring |
| `window_mgmt.py` | `list_windows`, `focus_window`, `minimize_window`, `maximize_window`, `close_window` | Window management |
| `volume.py` | `get_volume`, `set_volume`, `toggle_mute` | Volume control |
| `safety.py` | `ActionLogger`, blocklist, danger detection | Safety & audit layer |

### 4.3 Safety Features

* **Command Blocklist**: Dangerous commands (format drives, delete system files, modify boot config, diskpart) are **automatically refused**.
* **Action Logger**: Every single tool call is logged to `data/logs/actions_YYYY-MM-DD.jsonl` with timestamp, tool name, arguments, result, and status.
* **Danger Detection**: Commands matching destructive patterns (delete, kill, registry) are flagged.

### 4.4 Core Files

* `agent/graph.py`: Defines the ReAct agent graph — LLM node, tool node, conditional routing, system prompt.
* `agent/server.py`: FastAPI application that compiles the agent with Postgres checkpointer, serves endpoints and UI.
* `frontend/index.html`: Premium dark-mode chat interface with quick actions, thinking indicators, and markdown rendering.
* `system_tools/`: All tool modules (see table above).

### 4.5 Setup and Running

1. **Environment Setup**:
   Ensure your `.env` contains:
   - `DATABASE_URL` (Supabase connection string for the checkpointer memory)
   - `TAVILY_API_KEY` (For web search)
   - `GEMINI_API_KEY` (For the LangChain Google Generative AI integration)
   - `JARVIS_LOG_DIR` (Optional, default: `./data/logs`)
   - `JARVIS_SCREENSHOT_DIR` (Optional, default: `./data/screenshots`)

2. **Install Dependencies**:
   ```bash
   pip install pyautogui pillow psutil pyperclip pycaw comtypes pywin32
   ```

3. **Start the Server**:
   ```bash
   python run.py
   ```
   Or:
   ```bash
   uvicorn agent.server:app --host 127.0.0.1 --port 8000
   ```

4. **Usage**:
   Open `http://127.0.0.1:8000/` in your browser to interact with Jarvis.

5. **Standalone CLI** (no server needed):
   ```bash
   python -m agent.graph
   ```
   This runs Jarvis in your terminal with in-memory checkpointing.

### 4.6 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serve the Jarvis web UI |
| `/api/chat` | POST | Send a message to Jarvis (main endpoint) |
| `/api/research` | POST | Backward-compatible alias for `/api/chat` |
| `/api/actions/log` | GET | View Jarvis's action audit log |

---

## 5. Voice Communication & 24/7 Daemon (`voice/`)

Jarvis includes robust voice capabilities allowing for both web-based and standalone 24/7 background interaction.

### 5.1 Web UI Voice Integration
The Jarvis web interface (`frontend/index.html`) includes native **Speech-to-Text (STT)** and **Text-to-Speech (TTS)** using the browser's native Web Speech API.
* **Microphone (STT)**: Click the 🎙️ icon in the input bar to speak commands. It automatically transcribes and sends the message when you stop speaking.
* **Voice Output (TTS)**: Toggle the `🔊 Voice: OFF` button in the header to enable Jarvis to speak his responses out loud. Markdown is automatically stripped for a natural reading experience.

### 5.2 24/7 Native Background Daemon (`voice/daemon.py`)
For a true "always-on" experience, Jarvis has a standalone Python daemon that runs invisibly in the background of your OS, without needing a browser open.

* **Architecture**: Uses `sounddevice` to continuously listen in 5-second chunks (bypassing PyAudio Windows build issues), transcribes via Google STT, and routes commands directly to the FastAPI backend (`agent/server.py`).
* **Wake Word**: Continuously listens for the word **"Jarvis"**.
* **TTS Response**: Speaks back through your system audio using Windows' native `pyttsx3` engine.
* **Starting**: Simply run the `voice/start_daemon.bat` script provided, or: `python -m voice.daemon`

---

## 6. RAG Engine (`rag/`)

The RAG (Retrieval-Augmented Generation) engine provides local document search capabilities.

* `rag/engine.py`: Handles document loading (PDF, TXT, DOCX), chunking, vector store creation with ChromaDB, and retrieval-augmented question answering.
* `rag/test_engine.py`: Test suite for the RAG engine.
* Vector database stored at `data/chroma_db/`.

---

## 7. Legacy: Baby Jarvis Research Pipeline (`legacy/`)

The original multi-agent research pipeline is preserved in `legacy/pipeline.py` for backward compatibility and standalone testing.

### Architecture
* **Intake Agent**: Analyzes query, creates search plan
* **Researcher Agent**: Uses Tavily API for web search
* **Verifier Agent**: Fact-checks with retry loop (max 3 attempts)
* **Writer Agent**: Formats verified data into Markdown

### Running Standalone
```bash
python -m legacy.pipeline
```

---

## 8. Maintenance and Updates

> **Note to AI / Developers:**
> Whenever new features, models, endpoints, or agents are added to the project, this `DOCUMENTATION.md` file MUST be updated to keep an accurate single source of truth for the project's state.
