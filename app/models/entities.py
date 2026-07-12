from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class ChatSession(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=64)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(default="New Chat", max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id", index=True, max_length=64)
    role: str = Field(max_length=16)
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
