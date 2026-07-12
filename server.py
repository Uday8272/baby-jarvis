
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agent import workflow  # import the new ReAct agent graph

# load env vars (GEMINI_API_KEY, DATABASE_URL, TAVILY_API_KEY, etc.)
load_dotenv()

# ── helpers ──────────────────────────────────────────────────────────────────

def _try_postgres_checkpointer():
    """
    Attempt to connect to Supabase Postgres and return a PostgresSaver.
    Returns None if anything fails (missing DATABASE_URL, connection error, etc.)
    """
    raw_url = os.getenv("DATABASE_URL", "")
    if not raw_url:
        return None, None

    # strip the SQLAlchemy driver suffix so psycopg can connect directly
    db_uri = raw_url.replace("postgresql+psycopg://", "postgresql://")

    try:
        from psycopg import Connection
        from langgraph.checkpoint.postgres import PostgresSaver

        conn = Connection.connect(db_uri, autocommit=True, prepare_threshold=None)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        return checkpointer, conn
    except Exception as e:
        print(f"[WARN] Postgres checkpointer unavailable: {e}")
        print("[INFO] Falling back to in-memory checkpointer (no persistence across restarts).")
        return None, None


# ── global handle for the compiled graph ─────────────────────────────────────
agent_app = None   # set during lifespan startup
db_conn = None     # keep a reference so we can close it on shutdown


# ── FastAPI lifespan (replaces @app.on_event) ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
        1. Try to connect to Supabase Postgres for persistent memory.
        2. If that fails, use in-memory MemorySaver.
        3. Compile the LangGraph workflow with the chosen checkpointer.
    Shutdown:
        Close the database connection if one was opened.
    """
    global agent_app, db_conn

    checkpointer, db_conn = _try_postgres_checkpointer()

    if checkpointer:
        print("[OK] Postgres checkpointer ready — conversation memory is persistent.")
    else:
        checkpointer = MemorySaver()
        print("[OK] In-memory checkpointer ready — memory resets on restart.")

    # compile the ReAct agent graph with memory
    agent_app = workflow.compile(checkpointer=checkpointer)
    print("[OK] Jarvis ReAct agent compiled.")
    print("[OK] Tools: shell, files, apps, screen, keyboard, clipboard, sysinfo, windows, volume, web search, RAG (local docs)")

    yield  # ── app is running ──

    # shutdown: close the database connection if open
    if db_conn and not db_conn.closed:
        db_conn.close()
        print("[SHUTDOWN] Postgres checkpointer connection closed.")


# ── FastAPI application ──────────────────────────────────────────────────────

app = FastAPI(title="jarvis", lifespan=lifespan)


# ── request / response schemas ───────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None  # optional — a UUID is generated for new sessions


# ── endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def run_chat(request: QueryRequest):
    """
    Main endpoint — send a message to Jarvis.

    Jarvis will decide whether to use system tools, search the web,
    or just respond conversationally. Maintains conversation memory
    via the checkpointer.

    • If `session_id` is provided, continues an existing conversation.
    • If omitted, a fresh UUID is generated (new conversation).
    """
    # resolve the session id
    session_id = request.session_id.strip() if request.session_id else uuid.uuid4().hex

    # langgraph config — this is how the checkpointer knows which
    # conversation's memory to load / save
    config = {"configurable": {"thread_id": session_id}}

    input_state = {
        "messages": [HumanMessage(content=request.query)],
    }

    # invoke the ReAct agent (it will loop through tool calls automatically)
    result = agent_app.invoke(input_state, config=config)

    # get the final AI response (last message in the chain)
    ai_message = result["messages"][-1]
    raw_content = ai_message.content if hasattr(ai_message, "content") else ""

    # Gemini 2.5 Flash may return content as a list of content blocks
    # e.g. [{"type": "text", "text": "Hello!"}] — unwrap to plain string
    if isinstance(raw_content, list):
        response_text = " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw_content
        ).strip()
    elif isinstance(raw_content, str):
        response_text = raw_content
    else:
        response_text = str(raw_content)

    return {
        "result": response_text,
        "session_id": session_id,
    }


# Keep the old endpoint as an alias for backward compatibility
@app.post("/api/research")
async def run_research(request: QueryRequest):
    """Backward-compatible alias for /api/chat."""
    return await run_chat(request)


@app.get("/api/actions/log")
async def get_action_log(limit: int = 50):
    """
    View Jarvis's recent system action log.

    Returns the last N logged actions so you can see exactly what
    Jarvis has been doing on your machine.
    """
    from system_tools.safety import ActionLogger
    log = ActionLogger()
    entries = log.get_recent(n=limit)
    return {"actions": entries, "count": len(entries)}


@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serve the Jarvis frontend."""
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()