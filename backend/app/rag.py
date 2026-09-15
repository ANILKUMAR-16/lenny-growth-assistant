"""
backend/app/rag.py
RAG (Retrieval-Augmented Generation) engine for The Lenny Growth Assistant.

Responsibilities:
  - Generate embeddings with sentence-transformers (local, no API key)
  - Store and retrieve transcript chunks from pgvector
  - Route LLM requests to Ollama (local) or cloud providers (Anthropic / OpenAI)
  - Build citation-aware context prompts
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sentence_transformers import SentenceTransformer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import TranscriptChunk

logger = logging.getLogger(__name__)

# ── Embedding Model (loaded once at module import) ─────────────────────────────
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


def embed_text(text_input: str) -> list[float]:
    """Return a normalized embedding vector for the given text."""
    model = get_embedding_model()
    vec = model.encode(text_input, normalize_embeddings=True)
    return vec.tolist()


# ── pgvector Retrieval ─────────────────────────────────────────────────────────

async def retrieve_chunks(
    query: str,
    db: AsyncSession,
    top_k: int | None = None,
    threshold: float | None = None,
) -> list[dict[str, Any]]:
    """
    Embed the query and retrieve the top-k most similar transcript chunks
    from pgvector using cosine similarity.

    Returns a list of dicts with keys:
      {chunk_text, transcript_title, source_url, score}
    """
    top_k = top_k or settings.rag_top_k
    threshold = threshold or settings.rag_similarity_threshold

    query_vec = embed_text(query)

    # pgvector cosine distance operator: <=> (lower = more similar)
    # cosine similarity = 1 - distance
    stmt = text(
        """
        SELECT
            chunk_text,
            transcript_title,
            source_url,
            1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM transcript_chunks
        WHERE 1 - (embedding <=> CAST(:vec AS vector)) >= :threshold
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :top_k
        """
    )

    result = await db.execute(
        stmt,
        {
            "vec": json.dumps(query_vec),
            "threshold": threshold,
            "top_k": top_k,
        },
    )
    rows = result.fetchall()

    return [
        {
            "chunk_text": row.chunk_text,
            "transcript_title": row.transcript_title,
            "source_url": row.source_url,
            "score": float(row.score),
        }
        for row in rows
    ]


# ── Context & Citation Builder ─────────────────────────────────────────────────

def build_context_prompt(
    user_query: str,
    chunks: list[dict[str, Any]],
    system_prefix: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """
    Build a citation-grounded context prompt from retrieved RAG chunks.

    Returns:
      - The full prompt string to send to the LLM
      - A citations list for persisting to the DB
    """
    if not chunks:
        context_block = "No relevant transcript excerpts were found for this query."
        citations: list[dict[str, Any]] = []
    else:
        context_parts = []
        citations = []
        for i, chunk in enumerate(chunks, start=1):
            context_parts.append(
                f"[Source {i}] {chunk['transcript_title']} ({chunk['source_url']})\n"
                f"{chunk['chunk_text']}"
            )
            citations.append(
                {
                    "index": i,
                    "transcript_title": chunk["transcript_title"],
                    "source_url": chunk["source_url"],
                    "score": chunk["score"],
                }
            )
        context_block = "\n\n---\n\n".join(context_parts)

    base_system = system_prefix or (
        "You are The Lenny Growth Assistant, an expert AI advisor specializing in "
        "product growth, PLG (Product-Led Growth), and startup strategy. "
        "You draw exclusively from Lenny Rachitsky's podcast transcripts to ground your answers. "
        "Always cite sources using [Source N] notation. "
        "Be specific, actionable, and concise."
    )

    prompt = (
        f"{base_system}\n\n"
        f"## Relevant Transcript Excerpts\n\n"
        f"{context_block}\n\n"
        f"## User Question\n\n"
        f"{user_query}\n\n"
        f"## Your Answer\n\n"
        f"(Cite relevant sources with [Source N] as you answer.)"
    )

    return prompt, citations


# ── LLM Router ────────────────────────────────────────────────────────────────

async def call_llm(
    prompt: str,
    provider: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """
    Route a prompt to the configured LLM provider.

    provider override order:
      1. `provider` argument (from API request)
      2. settings.model_provider (from .env)

    Supported providers: "ollama", "anthropic", "openai"
    Falls back with a human-readable error message on connection failure.
    """
    effective_provider = (provider or settings.model_provider).lower()

    if effective_provider == "ollama":
        return await _call_ollama(prompt, max_tokens, temperature)
    elif effective_provider == "anthropic":
        return await _call_anthropic(prompt, max_tokens, temperature)
    elif effective_provider == "openai":
        return await _call_openai(prompt, max_tokens, temperature)
    else:
        raise ValueError(f"Unknown LLM provider: '{effective_provider}'. Use ollama | anthropic | openai")


async def _call_ollama(prompt: str, max_tokens: int, temperature: float) -> str:
    """Call the local Ollama API."""
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except httpx.ConnectError:
        logger.error("Ollama connection refused at %s", settings.ollama_base_url)
        raise ConnectionError(
            f"Could not connect to Ollama at {settings.ollama_base_url}. "
            "Please ensure Ollama is running locally (`ollama serve`) "
            f"and the model '{settings.ollama_model}' is pulled (`ollama pull {settings.ollama_model}`)."
        )
    except httpx.TimeoutException:
        raise TimeoutError(
            f"Ollama request timed out after {settings.ollama_timeout_seconds}s. "
            "The model may be loading or the prompt is too long."
        )
    except httpx.HTTPStatusError as e:
        logger.error("Ollama HTTP error: %s — %s", e.response.status_code, e.response.text)
        raise RuntimeError(f"Ollama returned an error: {e.response.status_code}")


async def _call_anthropic(prompt: str, max_tokens: int, temperature: float) -> str:
    """Call the Anthropic Claude API."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def _call_openai(prompt: str, max_tokens: int, temperature: float) -> str:
    """Call the OpenAI Chat Completions API."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


# ── Ollama Health Check ────────────────────────────────────────────────────────

async def ping_ollama() -> dict[str, Any]:
    """
    Check Ollama connectivity.
    Returns {"ok": bool, "model": str, "error": str | None}
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return {"ok": True, "available_models": models, "error": None}
    except Exception as e:
        return {"ok": False, "available_models": [], "error": str(e)}


# ── Chunk Ingestion Helper ────────────────────────────────────────────────────

async def upsert_chunk(
    db: AsyncSession,
    transcript_title: str,
    chunk_index: str,
    chunk_text: str,
    source_url: str,
) -> TranscriptChunk:
    """
    Insert a transcript chunk with its embedding, or skip if it already exists
    (based on the unique constraint on transcript_title + chunk_index).
    """
    # Check if chunk already exists
    existing = await db.execute(
        select(TranscriptChunk).where(
            TranscriptChunk.transcript_title == transcript_title,
            TranscriptChunk.chunk_index == chunk_index,
        )
    )
    chunk = existing.scalar_one_or_none()

    if chunk is not None:
        logger.debug("Chunk already exists: %s / %s — skipping", transcript_title, chunk_index)
        return chunk

    embedding = embed_text(chunk_text)
    chunk = TranscriptChunk(
        transcript_title=transcript_title,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        embedding=embedding,
        source_url=source_url,
    )
    db.add(chunk)
    await db.flush()
    return chunk
