from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _normalize_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def _make_engine(url: str):
    url = _normalize_url(url)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=300)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _drop_legacy_guest_schema() -> None:
    # Projects used to belong to anonymous invite-code guests; those rows cannot be mapped to
    # accounts, and create_all will not alter the existing tables.
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return
    if "guest_id" not in {c["name"] for c in inspector.get_columns("projects")}:
        return
    with engine.begin() as conn:
        for table in ("messages", "versions", "projects", "guests"):
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))


def init_db() -> None:
    from app import models  # noqa: F401

    _drop_legacy_guest_schema()
    Base.metadata.create_all(engine)
