"""
backend/app/main.py
FastAPI Application for The Lenny Growth Assistant.

Endpoints:
  GET  /health           — DB + Ollama connectivity checks
  POST /chat             — Main chat endpoint with RAG + artifact extraction
  POST /skills/ship30    — Ship 30 for 30 essay generator
  POST /ingest           — Seed transcript data into pgvector
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifact import extract_artifact
from app.config import settings
from app.db import Message, Session, TranscriptChunk, get_db, init_db, ping_db
from app.rag import (
    build_context_prompt,
    call_llm,
    ping_ollama,
    retrieve_chunks,
    upsert_chunk,
)
from app.skills.ship30 import generate_ship30_essay

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# ── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Lenny Growth Assistant API",
    description=(
        "A RAG-powered growth advisor grounded in Lenny Rachitsky's podcast transcripts. "
        "Supports local Ollama and cloud LLM providers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup / Shutdown ─────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Initializing database tables…")
    await init_db()
    logger.info("Database ready.")


# ── Request / Response Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, description="User message")
    session_id: str | None = Field(None, description="Existing session UUID (omit to create new)")
    model_provider: str | None = Field(
        None,
        description="Override LLM provider: ollama | anthropic | openai",
    )
    top_k: int | None = Field(None, ge=1, le=20, description="RAG retrieval top-k override")


class CitationModel(BaseModel):
    index: int
    transcript_title: str
    source_url: str
    score: float


class ArtifactModel(BaseModel):
    type: str  # "markdown" | "html" | "none"
    sanitized_content: str
    security_flags: list[str]
    is_sanitized: bool


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    role: str = "assistant"
    content: str
    citations: list[CitationModel]
    artifact: ArtifactModel
    provider_used: str


class Ship30Request(BaseModel):
    topic: str = Field(..., min_length=3, max_length=512, description="Essay topic")
    session_id: str | None = None
    model_provider: str | None = None
    top_k: int | None = Field(None, ge=1, le=20)


class Ship30Response(BaseModel):
    session_id: str
    topic: str
    essay: str
    word_count: int
    citations: list[CitationModel]
    provider_used: str


class IngestResponse(BaseModel):
    status: str
    transcripts_processed: int
    chunks_ingested: int


# ── /health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
async def health_check() -> dict[str, Any]:
    """
    Check database connectivity and Ollama availability.
    """
    db_ok = await ping_db()
    ollama_info = await ping_ollama()

    return {
        "status": "ok" if db_ok else "degraded",
        "database": {"ok": db_ok},
        "ollama": ollama_info,
        "model_provider": settings.model_provider,
        "embedding_model": settings.embedding_model,
    }


# ── /chat ─────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Main chat endpoint.

    Flow:
      1. Resolve or create a session
      2. Persist the user message
      3. Retrieve RAG chunks from pgvector
      4. Build context prompt with citations
      5. Call LLM (with provider override support)
      6. Extract and sanitize any artifact (Markdown/HTML)
      7. Persist the assistant message + citations
      8. Return the full response
    """
    # ── 1. Session ────────────────────────────────────────────────────────────
    session: Session | None = None
    if request.session_id:
        result = await db.execute(
            select(Session).where(Session.id == request.session_id)
        )
        session = result.scalar_one_or_none()
        

    if session is None:
        session = Session(user_metadata={})
        db.add(session)
        await db.flush()

    session_id_str = str(session.id)

    # ── 2. Persist user message ───────────────────────────────────────────────
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=request.message,
        citations=[],
    )
    db.add(user_msg)
    await db.flush()

    # ── 3. RAG retrieval ─────────────────────────────────────────────────────
    try:
        chunks = await retrieve_chunks(
            query=request.message,
            db=db,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.error("RAG retrieval failed: %s", e)
        chunks = []

    # ── 4. Build prompt ───────────────────────────────────────────────────────
    prompt, citations = build_context_prompt(
        user_query=request.message,
        chunks=chunks,
    )

    # ── 5. LLM call ───────────────────────────────────────────────────────────
    effective_provider = request.model_provider or settings.model_provider
    try:
        assistant_text = await call_llm(
            prompt=prompt,
            provider=request.model_provider,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {e}",
        )

    # ── 6. Artifact extraction ────────────────────────────────────────────────
    artifact_result = extract_artifact(assistant_text)

    # ── 7. Persist assistant message ─────────────────────────────────────────
    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=assistant_text,
        citations=citations,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    # ── 8. Return ─────────────────────────────────────────────────────────────
    return ChatResponse(
        session_id=session_id_str,
        message_id=str(assistant_msg.id),
        content=assistant_text,
        citations=[CitationModel(**c) for c in citations],
        artifact=ArtifactModel(**artifact_result.to_dict()),
        provider_used=effective_provider,
    )


# ── /skills/ship30 ────────────────────────────────────────────────────────────

@app.post("/skills/ship30", response_model=Ship30Response, tags=["Skills"])
async def ship30_essay(
    request: Ship30Request,
    db: AsyncSession = Depends(get_db),
) -> Ship30Response:
    """
    Generate a ~1,250-word Ship 30 for 30 essay on a growth/product topic,
    grounded in retrieved Lenny podcast transcripts.
    """
    # Session
    session: Session | None = None
    if request.session_id:
        result = await db.execute(
            select(Session).where(Session.id == uuid.UUID(request.session_id))
        )
        session = result.scalar_one_or_none()

    if session is None:
        session = Session(user_metadata={"skill": "ship30"})
        db.add(session)
        await db.flush()

    # RAG retrieval on the topic
    try:
        chunks = await retrieve_chunks(
            query=request.topic,
            db=db,
            top_k=request.top_k or settings.rag_top_k,
        )
    except Exception as e:
        logger.error("RAG retrieval failed for ship30: %s", e)
        chunks = []

    # Generate essay
    try:
        result_data = await generate_ship30_essay(
            topic=request.topic,
            chunks=chunks,
            provider=request.model_provider,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ship30 generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Essay generation failed: {e}",
        )

    # Persist as messages
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=f"[Ship 30] Write an essay about: {request.topic}",
        citations=[],
    )
    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=result_data["essay"],
        citations=result_data["citations"],
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    return Ship30Response(
        session_id=str(session.id),
        topic=result_data["topic"],
        essay=result_data["essay"],
        word_count=result_data["word_count"],
        citations=[CitationModel(**c) for c in result_data["citations"]],
        provider_used=result_data["provider_used"],
    )


# ── /ingest ───────────────────────────────────────────────────────────────────

@app.post("/ingest", response_model=IngestResponse, tags=["Data"])
async def ingest_transcripts(
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """
    Seed the `data/sample_transcripts.json` file into the pgvector store.
    Safe to call multiple times — uses upsert semantics.
    """
    data_path = Path(__file__).parent.parent.parent / "data" / "sample_transcripts.json"
    if not data_path.exists():
        data_path = Path("/app/data/sample_transcripts.json")
    if not data_path.exists():
        data_path = Path(__file__).parent.parent / "data" / "sample_transcripts.json"

    if not data_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data file not found at {data_path}",
        )

    transcripts = json.loads(data_path.read_text(encoding="utf-8"))
    total_chunks = 0
    transcripts_processed = 0

    for transcript in transcripts:
        title = transcript["title"]
        source_url = transcript["source_url"]
        chunks = transcript.get("chunks", [])

        for i, chunk in enumerate(chunks):
            await upsert_chunk(
                db=db,
                transcript_title=title,
                chunk_index=chunk.get("timestamp", str(i)),
                chunk_text=chunk["text"],
                source_url=source_url,
            )
            total_chunks += 1

        transcripts_processed += 1

    await db.commit()
    logger.info(
        "Ingested %d chunks from %d transcripts",
        total_chunks,
        transcripts_processed,
    )

    return IngestResponse(
        status="success",
        transcripts_processed=transcripts_processed,
        chunks_ingested=total_chunks,
    )


# ── Session History (bonus) ───────────────────────────────────────────────────

@app.get("/sessions/{session_id}/history", tags=["Chat"])
async def get_session_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the full message history for a session."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id UUID format")

    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()

    return {
        "session": session.to_dict(),
        "messages": [m.to_dict() for m in messages],
    }
