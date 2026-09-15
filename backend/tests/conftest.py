"""
backend/tests/conftest.py
Shared pytest configuration and fixtures.

Uses SQLite (aiosqlite) for test isolation.
Patches pgvector Vector and PostgreSQL UUID types to be SQLite-compatible.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# ── Ensure app is importable ───────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Override settings BEFORE any app module imports ────────────────────────────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_lenny.db"
os.environ["MODEL_PROVIDER"] = "ollama"
os.environ["EMBEDDING_MODEL"] = "all-MiniLM-L6-v2"
os.environ["EMBEDDING_DIM"] = "384"
os.environ["RAG_TOP_K"] = "5"
os.environ["RAG_SIMILARITY_THRESHOLD"] = "0.3"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["APP_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret"

# ── Patch pgvector Vector to use Text for SQLite compatibility ─────────────────
from unittest.mock import MagicMock
from sqlalchemy import Text

# Create a mock Vector class that returns Text column type
class FakeVector(Text):
    """SQLite-compatible stub for pgvector.sqlalchemy.Vector."""
    def __init__(self, dim=384):
        super().__init__()
        self.dim = dim

import pgvector.sqlalchemy as _pgvec
_pgvec.Vector = FakeVector

# Also patch the UUID dialect type to plain String for SQLite
from sqlalchemy import String
import sqlalchemy.dialects.postgresql as _pg
_original_uuid_cls = _pg.UUID
class FakeUUID(String):
    """SQLite-compatible UUID type that stores UUIDs as strings."""

    def __init__(self, as_uuid=False, *args, **kwargs):
        super().__init__(length=36)
        self.as_uuid = as_uuid

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            return str(value)
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            return value
        return process
_pg.UUID = FakeUUID


# Also patch JSON for SQLite (JSON is supported in SQLite but let's be safe)
# SQLAlchemy's JSON type works with SQLite natively, so no patch needed.
