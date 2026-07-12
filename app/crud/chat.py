from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import ChatSession, Message, User


def get_or_create_user(session: Session, username: str) -> User:
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if user:
        return user

    user = User(username=username)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_or_create_chat_session(session: Session, session_id: str, user_id: int) -> ChatSession:
    chat_session = session.get(ChatSession, session_id)
    if chat_session:
        return chat_session

    chat_session = ChatSession(id=session_id, user_id=user_id)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def touch_session(session: Session, chat_session: ChatSession) -> None:
    chat_session.updated_at = datetime.now(timezone.utc)
    session.add(chat_session)
    session.commit()


def create_message(session: Session, session_id: str, role: str, content: str) -> Message:
    message = Message(session_id=session_id, role=role, content=content)
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def get_recent_messages(session: Session, session_id: str, limit: int) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    rows = session.exec(statement).all()
    rows.reverse()
    return rows


def list_user_chat_sessions(session: Session, user_id: int, limit: int = 100) -> list[ChatSession]:
    statement = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
        .limit(limit)
    )
    return session.exec(statement).all()


def list_messages_for_session(session: Session, session_id: str, user_id: int, limit: int = 200) -> list[Message]:
    session_statement = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    chat_session = session.exec(session_statement).first()
    if not chat_session:
        return []

    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(limit)
    )
    return session.exec(statement).all()
