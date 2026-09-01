"""
SQLAlchemy engine, session factory, and declarative base.

Every model in app/models imports Base from here. Every endpoint that needs
the database depends on get_db(), which hands out one session per request
and always closes it — including on error.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, guarantees it's closed afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
