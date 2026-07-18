"""SQLAlchemy engine and session construction without schema side effects."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url_from_env() -> str:
    """Return the configured database URL without overriding process settings."""
    load_dotenv(override=False)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for database operations.")
    return database_url


def build_engine(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Build an engine; callers remain responsible for running migrations."""
    return create_engine(database_url or database_url_from_env(), echo=echo, pool_pre_ping=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the shared session boundary used by persistence services."""
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
