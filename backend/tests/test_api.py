"""
backend/tests/test_api.py
Integration tests for The Lenny Growth Assistant FastAPI endpoints.

Uses SQLite (aiosqlite) for isolation.
Ollama and cloud LLM calls are mocked.
DB patching is done in conftest.py.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from pathlib import Path
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base, get_db
from app.main import app

# ── Test DB Setup ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///./test_lenny.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables in the test SQLite DB before any tests run."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    # Clean up test DB file
    db_file = Path("./test_lenny.db")
    if db_file.exists():
        db_file.unlink()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── /health tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient):
    """Health endpoint should always return 200 with a status field."""
    with patch("app.main.ping_db", new_callable=AsyncMock, return_value=True), \
         patch("app.main.ping_ollama", new_callable=AsyncMock, return_value={"ok": True, "available_models": ["llama3.2"], "error": None}):
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "ollama" in data


@pytest.mark.asyncio
async def test_health_shows_degraded_when_db_down(client: AsyncClient):
    """Health endpoint should show 'degraded' when DB is unreachable."""
    with patch("app.main.ping_db", new_callable=AsyncMock, return_value=False), \
         patch("app.main.ping_ollama", new_callable=AsyncMock, return_value={"ok": False, "available_models": [], "error": "connection refused"}):
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"]["ok"] is False


# ── /chat tests ───────────────────────────────────────────────────────────────

MOCK_LLM_RESPONSE = (
    "Great question! Based on Airbnb's playbook [Source 1], product-market fit is felt "
    "when users pull the product rather than you pushing it. "
    "The key growth loop at Airbnb was: guest books → great experience → tells friends [Source 1]."
)


@pytest.mark.asyncio
async def test_chat_creates_new_session(client: AsyncClient):
    """Chat should create a new session when none is provided."""
    with patch("app.main.retrieve_chunks", new_callable=AsyncMock, return_value=[]), \
         patch("app.main.call_llm", new_callable=AsyncMock, return_value=MOCK_LLM_RESPONSE):
        response = await client.post(
            "/chat",
            json={"message": "What is product-market fit?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["session_id"] is not None
    assert data["role"] == "assistant"
    assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_chat_reuses_existing_session(client: AsyncClient):
    """Chat should reuse an existing session_id across turns."""
    with patch("app.main.retrieve_chunks", new_callable=AsyncMock, return_value=[]), \
         patch("app.main.call_llm", new_callable=AsyncMock, return_value=MOCK_LLM_RESPONSE):
        # First turn
        r1 = await client.post("/chat", json={"message": "Tell me about growth loops."})
        assert r1.status_code == 200
        session_id = r1.json()["session_id"]

        # Second turn with same session
        r2 = await client.post(
            "/chat",
            json={"message": "Give me a specific example.", "session_id": session_id},
        )
        assert r2.status_code == 200
        assert r2.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_chat_with_rag_citations(client: AsyncClient):
    """Chat should include citations from RAG retrieval."""
    mock_chunks = [
        {
            "chunk_text": "Airbnb's Craigslist integration drove their first viral growth spike.",
            "transcript_title": "How Airbnb Achieved Product-Market Fit",
            "source_url": "https://www.lennyspodcast.com/how-airbnb-achieved-product-market-fit/",
            "score": 0.91,
        }
    ]

    with patch("app.main.retrieve_chunks", new_callable=AsyncMock, return_value=mock_chunks), \
         patch("app.main.call_llm", new_callable=AsyncMock, return_value=MOCK_LLM_RESPONSE):
        response = await client.post(
            "/chat",
            json={"message": "How did Airbnb grow early on?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) == 1
    assert data["citations"][0]["transcript_title"] == "How Airbnb Achieved Product-Market Fit"
    assert data["citations"][0]["score"] == 0.91


@pytest.mark.asyncio
async def test_chat_rejects_empty_message(client: AsyncClient):
    """Chat should reject empty messages with a 422 Unprocessable Entity."""
    response = await client.post("/chat", json={"message": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_handles_ollama_connection_error(client: AsyncClient):
    """Chat should return 503 when Ollama is unreachable."""
    with patch("app.main.retrieve_chunks", new_callable=AsyncMock, return_value=[]), \
         patch("app.main.call_llm", new_callable=AsyncMock, side_effect=ConnectionError("Ollama not running")):
        response = await client.post(
            "/chat",
            json={"message": "What is a referral loop?"},
        )

    assert response.status_code == 503
    assert "Ollama" in response.json()["detail"] or "not running" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_artifact_detected(client: AsyncClient):
    """Chat should detect and return artifact metadata when LLM returns Markdown."""
    md_response = """Here is a summary:

```markdown
# Growth Loop Analysis

## Key Insight
- **Airbnb** used Craigslist integration [Source 1]
- **PayPal** targeted eBay power users [Source 2]

## The 1 Big Takeaway
Find your super-users and design the referral mechanism around their natural behavior.
```
"""
    with patch("app.main.retrieve_chunks", new_callable=AsyncMock, return_value=[]), \
         patch("app.main.call_llm", new_callable=AsyncMock, return_value=md_response):
        response = await client.post(
            "/chat",
            json={"message": "Summarize growth loops as markdown"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["artifact"]["type"] == "markdown"
    assert "Growth Loop Analysis" in data["artifact"]["sanitized_content"]


# ── /ingest tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_returns_success(client: AsyncClient):
    """Ingest endpoint should return success with chunk counts."""
    # Mock upsert_chunk to avoid actual embedding computation
    with patch("app.main.upsert_chunk", new_callable=AsyncMock):
        response = await client.post("/ingest")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["transcripts_processed"] >= 1
    assert data["chunks_ingested"] >= 1


# ── /sessions/{id}/history tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_history_returns_messages(client: AsyncClient):
    """Session history endpoint should return persisted messages."""
    with patch("app.main.retrieve_chunks", new_callable=AsyncMock, return_value=[]), \
         patch("app.main.call_llm", new_callable=AsyncMock, return_value="A helpful response about growth."):
        chat_resp = await client.post(
            "/chat",
            json={"message": "What is PLG?"},
        )
    assert chat_resp.status_code == 200
    session_id = chat_resp.json()["session_id"]

    history_resp = await client.get(f"/sessions/{session_id}/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert "messages" in history
    assert len(history["messages"]) >= 2  # user + assistant


@pytest.mark.asyncio
async def test_session_history_invalid_uuid(client: AsyncClient):
    """Session history should return 400 for invalid UUID format."""
    response = await client.get("/sessions/not-a-valid-uuid/history")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_session_history_not_found(client: AsyncClient):
    """Session history should return 404 for non-existent sessions."""
    import uuid
    response = await client.get(f"/sessions/{uuid.uuid4()}/history")
    assert response.status_code == 404
