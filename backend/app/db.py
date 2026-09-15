"""
backend/app/db.py
PostgreSQL + pgvector database layer for The Lenny Growth Assistant.

Tables:
  - sessions          : conversation sessions
  - messages          : chat messages with citations (JSONB)
  - transcript_chunks : RAG knowledge base with pgvector embeddings
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import settings


# ── SQLAlchemy Base ────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Models ────────────────────────────────────────────────────────────────────

class Session(Base):
    """
    Represents a conversation session.
    user_metadata is a free-form JSONB blob (browser fingerprint, user_agent, etc.)
    """

    __tablename__ = "sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    user_metadata = Column(JSON, nullable=True)

    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "user_metadata": self.user_metadata,
        }


class Message(Base):
    """
    A single chat turn (user or assistant).
    citations stores a list of {title, url, chunk_index, score} dicts.
    """

    __tablename__ = "messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True, default=list)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session = relationship("Session", back_populates="messages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "citations": self.citations or [],
            "created_at": self.created_at.isoformat(),
        }


class TranscriptChunk(Base):
    """
    A chunk of a Lenny podcast transcript, stored with a pgvector embedding
    for semantic similarity retrieval.
    """

    __tablename__ = "transcript_chunks"
    __table_args__ = (
        UniqueConstraint("transcript_title", "chunk_index", name="uq_chunk_identity"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    transcript_title = Column(String(512), nullable=False, index=True)
    chunk_index = Column(String(16), nullable=False)   # e.g. "0", "1", timestamp
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dim), nullable=True)
    source_url = Column(String(2048), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "transcript_title": self.transcript_title,
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "source_url": self.source_url,
        }


# ── Engine & Session Factory ───────────────────────────────────────────────────

if settings.database_url.startswith("sqlite"):
    engine = create_async_engine(
        settings.database_url,
        echo=settings.is_development(),
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.is_development(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Enable the pgvector extension and create all tables.
    Safe to call on every startup (CREATE IF NOT EXISTS semantics).
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields an async database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ping_db() -> bool:
    """
    Check if the database is reachable.
    Returns True on success, False on error.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
