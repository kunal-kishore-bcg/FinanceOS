"""
SQLAlchemy engine and session setup.

Alembic (see /backend/alembic) owns schema creation — this module
deliberately never calls Base.metadata.create_all(), so migration
history stays the single source of truth for schema state (brief
6.4: "DB migrations must be repeatable").
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency for a scoped DB session. Not wired into any
    routes yet — no API layer exists this phase — but defined here so
    the pattern is settled before route code is written.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
