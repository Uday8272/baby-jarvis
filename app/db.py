from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings
from app.models import entities as _entities_models  # noqa: F401


settings = get_settings()
is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
