import httpx
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session

from app.config import Settings, get_settings
from app.crud.chat import (
    create_message,
    get_or_create_chat_session,
    get_or_create_user,
    get_recent_messages,
    list_messages_for_session,
    list_user_chat_sessions,
    touch_session,
)
from app.db import engine, get_session, init_db
from app.security import authenticate_owner, create_access_token, get_current_owner
from app.services.conversation import build_prompt_with_memory
from app.services.llm import AsyncLLMService, LLMGenerationRequest, get_llm_service


app = FastAPI(
    title="JARVIS API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


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


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    settings = get_settings()
    with Session(engine) as session:
        get_or_create_user(session, settings.owner_username)


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
    llm_service: AsyncLLMService = Depends(llm_service_dependency),
) -> ChatResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required.")

    owner_user = get_or_create_user(session, settings.owner_username)
    if owner_user.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Owner user missing id.")
    session_id = payload.session_id.strip() if payload.session_id else uuid4().hex
    chat_session = get_or_create_chat_session(session, session_id, owner_user.id)
    recent_messages = get_recent_messages(session, session_id, settings.memory_window_messages)
    prompt = build_prompt_with_memory(payload.text, recent_messages)

    try:
        generated_text = await llm_service.generate_text(
            LLMGenerationRequest(
                prompt=prompt,
                temperature=payload.temperature,
                max_output_tokens=payload.max_output_tokens,
            )
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream LLM returned an error: {exc.response.status_code}.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach configured LLM provider.",
        ) from exc
    except RuntimeError as exc:
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
