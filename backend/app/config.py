"""
backend/app/config.py
Pydantic Settings for The Lenny Growth Assistant.
Reads from .env file; supports Ollama (local) and cloud LLM providers.
"""

from __future__ import annotations

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_db",
        description="Async SQLAlchemy database URL",
    )

    # ── LLM Provider ──────────────────────────────────────────────────────────
    model_provider: Literal["ollama", "anthropic", "openai"] = Field(
        default="ollama",
        description="Which LLM backend to use: ollama | anthropic | openai",
    )

    # ── Ollama (Local) ────────────────────────────────────────────────────────
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model name",
    )
    ollama_timeout_seconds: float = Field(
        default=600.0,
        description="HTTP timeout for Ollama requests",
    )

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic model name",
    )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model name",
    )

    # ── Embedding ─────────────────────────────────────────────────────────────
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings",
    )
    embedding_dim: int = Field(
        default=384,
        description="Embedding vector dimension",
    )

    # ── RAG ───────────────────────────────────────────────────────────────────
    rag_top_k: int = Field(
        default=5,
        description="Number of RAG chunks to retrieve",
    )
    rag_similarity_threshold: float = Field(
        default=0.3,
        description="Minimum cosine similarity score for a chunk to be included",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )
    secret_key: str = Field(
        default="dev-secret-change-in-production",
        description="Application secret key",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v  # kept as string; split at usage site

    def get_cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


# ── Singleton ─────────────────────────────────────────────────────────────────
settings = Settings()
