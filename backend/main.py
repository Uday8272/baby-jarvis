import httpx
from uuid import uuid4
import os
from contextlib import asynccontextmanager
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agent.graph import workflow
from agent.scheduler.engine import get_scheduler
from agent.scheduler.jobs import set_agent_app
from agent.scheduler.watcher import stop_all_watchers

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
import subprocess
import atexit
import sys
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session

from backend.config import Settings, get_settings
from backend.crud.chat import (
    create_message,
    get_or_create_chat_session,
    get_or_create_user,
    get_recent_messages,
    list_messages_for_session,
    list_user_chat_sessions,
    touch_session,
)
from backend.db import engine, get_session, init_db
from backend.security import authenticate_owner, create_access_token, get_current_owner
from backend.services.conversation import build_prompt_with_memory
from backend.services.llm import AsyncLLMService, LLMGenerationRequest, get_llm_service


# ── global handle for the compiled graph ─────────────────────────────────────
agent_app = None   # set during lifespan startup
db_conn = None     # keep a reference so we can close it on shutdown

def _try_postgres_checkpointer():
    settings = get_settings()
    raw_url = settings.database_url
    if not raw_url:
        return None, None
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
        return None, None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_app, db_conn
    voice_process = None

    # original backend startup logic
    init_db()
    settings = get_settings()
    with Session(engine) as session:
        get_or_create_user(session, settings.owner_username)

    # agent and scheduler startup logic
    checkpointer, db_conn = _try_postgres_checkpointer()
    if not checkpointer:
        checkpointer = MemorySaver()
    
    agent_app = workflow.compile(checkpointer=checkpointer)
    task_scheduler = get_scheduler()
    task_scheduler.start()
    set_agent_app(agent_app)

    # Start Voice Daemon
    voice_script = os.path.join(os.path.dirname(__file__), "..", "voice", "daemon.py")
    python_exe = sys.executable
    voice_process = subprocess.Popen([python_exe, voice_script])
    
    yield

    if db_conn and not db_conn.closed:
        db_conn.close()
    
    try:
        task_scheduler = get_scheduler()
        task_scheduler.shutdown(wait=False)
    except Exception:
        pass
    stop_all_watchers()
    
    if voice_process:
        voice_process.terminate()
        try:
            voice_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            voice_process.kill()


app = FastAPI(
    title="JARVIS API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

# Serve static frontend files (style.css, app.js, etc.)
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/frontend", StaticFiles(directory=_frontend_dir), name="frontend")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ChatRequest(BaseModel):
    text: str
    session_id: str | None = None
    temperature: float = 0.2
    max_output_tokens: int = 512


class ChatResponse(BaseModel):
    session_id: str
    response: str


class ChatSessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


def llm_service_dependency(settings: Settings = Depends(get_settings)) -> AsyncLLMService:
    return get_llm_service(settings)





@app.post("/auth/token", response_model=TokenResponse)
def issue_owner_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if not authenticate_owner(form_data.username, form_data.password, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(settings.owner_username, settings),
        token_type="bearer",
    )


@app.get("/")
def jarvis_entrypoint(owner: str = Depends(get_current_owner)) -> dict[str, str]:
    return {"message": f"Access granted. Welcome back, {owner}."}


@app.get("/auth/whoami")
def whoami(owner: str = Depends(get_current_owner)) -> dict[str, str]:
    return {"owner": owner}


@app.post("/chat", response_model=ChatResponse)
async def chat_with_jarvis(
    payload: ChatRequest,
    _owner: str = Depends(get_current_owner),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> ChatResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required.")

    owner_user = get_or_create_user(session, settings.owner_username)
    if owner_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Owner user missing id.")
    session_id = payload.session_id.strip() if payload.session_id else uuid4().hex
    chat_session = get_or_create_chat_session(session, session_id, owner_user.id)
    
    config = {"configurable": {"thread_id": session_id}}
    input_state = {"messages": [HumanMessage(content=payload.text.strip())]}

    try:
        result = agent_app.invoke(input_state, config=config)
        
        ai_message = result["messages"][-1]
        raw_content = ai_message.content if hasattr(ai_message, "content") else ""

        if isinstance(raw_content, list):
            generated_text = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_content
            ).strip()
        else:
            generated_text = str(raw_content)
            
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    create_message(session, session_id, "user", payload.text.strip())
    create_message(session, session_id, "assistant", generated_text)
    touch_session(session, chat_session)

    return ChatResponse(session_id=session_id, response=generated_text)


@app.get("/chat/sessions", response_model=list[ChatSessionSummary])
def get_chat_sessions(
    _owner: str = Depends(get_current_owner),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> list[ChatSessionSummary]:
    owner_user = get_or_create_user(session, settings.owner_username)
    if owner_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Owner user missing id.")
    sessions = list_user_chat_sessions(session, owner_user.id)
    return [
        ChatSessionSummary(
            session_id=item.id,
            title=item.title,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )
        for item in sessions
    ]


@app.get("/chat/sessions/{session_id}/messages", response_model=list[MessageResponse])
def get_chat_session_messages(
    session_id: str,
    _owner: str = Depends(get_current_owner),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> list[MessageResponse]:
    owner_user = get_or_create_user(session, settings.owner_username)
    if owner_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Owner user missing id.")
    messages = list_messages_for_session(session, session_id, owner_user.id)
    return [
        MessageResponse(
            id=item.id or 0,
            role=item.role,
            content=item.content,
            created_at=item.created_at.isoformat(),
        )
        for item in messages
    ]


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None

# Backward compatibility alias for the frontend UI before we build the login screen
@app.post("/api/chat")
async def run_chat(request: QueryRequest):
    # This acts as an unauthenticated fallback for the existing local frontend UI
    # It directly invokes the agent_app without tracking to SQL DB
    session_id = request.session_id.strip() if request.session_id else uuid4().hex
    config = {"configurable": {"thread_id": session_id}}
    input_state = {"messages": [HumanMessage(content=request.query)]}
    result = agent_app.invoke(input_state, config=config)
    ai_message = result["messages"][-1]
    raw_content = ai_message.content if hasattr(ai_message, "content") else ""
    if isinstance(raw_content, list):
        response_text = " ".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in raw_content).strip()
    else:
        response_text = str(raw_content)
    return {"result": response_text, "session_id": session_id}


@app.get("/api/actions/log")
async def get_action_log(limit: int = 50):
    from agent.tools.safety import ActionLogger
    log = ActionLogger()
    entries = log.get_recent(n=limit)
    return {"actions": entries, "count": len(entries)}


@app.get("/ui", response_class=HTMLResponse)
async def get_ui():
    html_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()