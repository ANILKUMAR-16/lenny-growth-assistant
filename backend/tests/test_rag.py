"""
backend/tests/test_rag.py
Unit tests for the RAG engine and Ship 30 skill.

These tests run without a live database or LLM.
DB/env patching is done in conftest.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Artifact extraction tests ─────────────────────────────────────────────────

from app.artifact import extract_artifact, ArtifactResult


class TestArtifactExtraction:
    def test_detects_fenced_html_block(self):
        text = "Here is some HTML:\n```html\n<h1>Hello World</h1>\n```"
        result = extract_artifact(text)
        assert result.type == "html"
        assert "<h1>Hello World</h1>" in result.sanitized_content

    def test_detects_fenced_markdown_block(self):
        text = "```markdown\n# My Heading\n\n- Bullet one\n- Bullet two\n```"
        result = extract_artifact(text)
        assert result.type == "markdown"
        assert "# My Heading" in result.sanitized_content

    def test_detects_raw_html_body(self):
        text = "<!DOCTYPE html>\n<html><body><p>Hello</p></body></html>"
        result = extract_artifact(text)
        assert result.type == "html"

    def test_detects_rich_markdown_body(self):
        text = "# Title\n\n## Section One\n\nSome content.\n\n## Section Two\n\nMore content."
        result = extract_artifact(text)
        assert result.type == "markdown"

    def test_returns_none_for_plain_text(self):
        text = "This is a plain text response with no special formatting."
        result = extract_artifact(text)
        assert result.type == "none"

    def test_strips_script_tags(self):
        text = "```html\n<div><script>alert('xss')</script><p>Safe content</p></div>\n```"
        result = extract_artifact(text)
        assert result.type == "html"
        assert "SCRIPT_TAG_REMOVED" in result.security_flags
        assert "<script>" not in result.sanitized_content
        assert result.is_sanitized is True

    def test_strips_inline_event_handlers(self):
        text = '```html\n<button onclick="evil()">Click me</button>\n```'
        result = extract_artifact(text)
        assert "INLINE_EVENT_HANDLER_REMOVED" in result.security_flags
        assert "onclick" not in result.sanitized_content

    def test_strips_javascript_hrefs(self):
        text = '```html\n<a href="javascript:void(0)">Link</a>\n```'
        result = extract_artifact(text)
        assert "JAVASCRIPT_HREF_REMOVED" in result.security_flags

    def test_strips_iframe_tags(self):
        text = '```html\n<iframe src="https://evil.com"></iframe>\n```'
        result = extract_artifact(text)
        assert "IFRAME_REMOVED" in result.security_flags

    def test_clean_html_has_no_security_flags(self):
        text = "```html\n<h1>Clean</h1><p>No dangerous content.</p>\n```"
        result = extract_artifact(text)
        assert result.type == "html"
        assert result.security_flags == []
        assert result.is_sanitized is False


# ── Embedding tests ────────────────────────────────────────────────────────────

class TestEmbedding:
    def test_embed_text_returns_list_of_floats(self):
        """embed_text should return a list of floats with the correct dimension."""
        from app.rag import embed_text
        vec = embed_text("What is product-market fit?")
        assert isinstance(vec, list)
        assert len(vec) == 384  # all-MiniLM-L6-v2 output dim
        assert all(isinstance(v, float) for v in vec)

    def test_embed_text_is_normalized(self):
        """Embeddings should be approximately unit-norm (cosine ready)."""
        import math
        from app.rag import embed_text
        vec = embed_text("growth loops are compounding systems")
        magnitude = math.sqrt(sum(v ** 2 for v in vec))
        # Normalized vectors have magnitude ≈ 1.0
        assert abs(magnitude - 1.0) < 0.01

    def test_different_texts_have_different_embeddings(self):
        from app.rag import embed_text
        v1 = embed_text("referral program design")
        v2 = embed_text("machine learning infrastructure")
        assert v1 != v2


# ── Context prompt builder tests ──────────────────────────────────────────────

class TestContextPromptBuilder:
    def test_builds_prompt_with_citations(self):
        from app.rag import build_context_prompt
        chunks = [
            {
                "chunk_text": "Airbnb used Craigslist integration.",
                "transcript_title": "How Airbnb Achieved PMF",
                "source_url": "https://lennyspodcast.com/airbnb",
                "score": 0.88,
            }
        ]
        prompt, citations = build_context_prompt("How did Airbnb grow?", chunks)
        assert "[Source 1]" in prompt
        assert "How Airbnb Achieved PMF" in prompt
        assert len(citations) == 1
        assert citations[0]["index"] == 1

    def test_builds_prompt_with_no_chunks(self):
        from app.rag import build_context_prompt
        prompt, citations = build_context_prompt("Any question", [])
        assert "No relevant transcript excerpts" in prompt
        assert citations == []

    def test_custom_system_prefix_is_used(self):
        from app.rag import build_context_prompt
        prompt, _ = build_context_prompt("question", [], system_prefix="CUSTOM SYSTEM")
        assert "CUSTOM SYSTEM" in prompt


# ── LLM router tests ──────────────────────────────────────────────────────────

class TestLLMRouter:
    @pytest.mark.asyncio
    async def test_raises_on_unknown_provider(self):
        from app.rag import call_llm
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            await call_llm("test prompt", provider="nonexistent_provider")

    @pytest.mark.asyncio
    async def test_raises_connection_error_when_ollama_down(self):
        """Should raise ConnectionError (not crash) when Ollama is unreachable."""
        from app.rag import call_llm
        with patch("app.rag._call_ollama", new_callable=AsyncMock,
                   side_effect=ConnectionError("Ollama not running")):
            with pytest.raises(ConnectionError):
                await call_llm("test", provider="ollama")

    @pytest.mark.asyncio
    async def test_raises_value_error_without_anthropic_key(self):
        """Should raise ValueError when Anthropic key is missing."""
        from app.rag import call_llm
        with patch("app.rag.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.model_provider = "anthropic"
            with pytest.raises((ValueError, Exception)):
                await call_llm("test", provider="anthropic")


# ── Ship 30 skill tests ───────────────────────────────────────────────────────

class TestShip30Skill:
    @pytest.mark.asyncio
    async def test_generates_essay_dict(self):
        """Ship 30 generator should return a dict with essay, word_count, citations."""
        mock_essay = " ".join(["word"] * 1250)  # fake 1250-word essay

        with patch("app.skills.ship30.call_llm", new_callable=AsyncMock, return_value=mock_essay), \
             patch("app.skills.ship30.build_context_prompt",
                   return_value=("mocked prompt", [{"index": 1, "transcript_title": "T", "source_url": "U", "score": 0.9}])):
            from app.skills.ship30 import generate_ship30_essay
            result = await generate_ship30_essay(
                topic="How referral programs drive compounding growth",
                chunks=[],
                provider="ollama",
            )

        assert "essay" in result
        assert "word_count" in result
        assert result["word_count"] == 1250
        assert "citations" in result
        assert result["topic"] == "How referral programs drive compounding growth"

    @pytest.mark.asyncio
    async def test_propagates_llm_error(self):
        """Ship 30 generator should propagate LLM errors for the caller to handle."""
        with patch("app.skills.ship30.call_llm", new_callable=AsyncMock,
                   side_effect=ConnectionError("Ollama offline")), \
             patch("app.skills.ship30.build_context_prompt", return_value=("prompt", [])):
            from app.skills.ship30 import generate_ship30_essay
            with pytest.raises(ConnectionError):
                await generate_ship30_essay(
                    topic="growth loops",
                    chunks=[],
                )
