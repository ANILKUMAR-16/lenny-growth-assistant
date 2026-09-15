"""
backend/app/artifact.py
Artifact detection and security validation for The Lenny Growth Assistant.

Responsibilities:
  - Detect Markdown or HTML/CSS blocks in LLM responses
  - Strip dangerous HTML patterns (script tags, event handlers)
  - Return structured metadata for the frontend ArtifactViewer
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


ArtifactType = Literal["markdown", "html", "none"]


# ── Regexes ───────────────────────────────────────────────────────────────────

# Fenced code blocks
_FENCED_HTML_RE = re.compile(
    r"```(?:html|HTML)\s*\n(.*?)```",
    re.DOTALL,
)
_FENCED_MD_RE = re.compile(
    r"```(?:markdown|md)\s*\n(.*?)```",
    re.DOTALL,
)

# Security patterns to flag / strip
_SCRIPT_TAG_RE = re.compile(
    r"<\s*script[\s>].*?</\s*script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_INLINE_EVENT_RE = re.compile(
    r'\s+on\w+\s*=\s*["\'][^"\']*["\']',
    re.IGNORECASE,
)
_JAVASCRIPT_HREF_RE = re.compile(
    r'href\s*=\s*["\']javascript:[^"\']*["\']',
    re.IGNORECASE,
)
_IFRAME_RE = re.compile(
    r"<\s*iframe[\s>].*?</\s*iframe\s*>",
    re.IGNORECASE | re.DOTALL,
)
_OBJECT_EMBED_RE = re.compile(
    r"<\s*(object|embed|applet)[\s>].*?</\s*(object|embed|applet)\s*>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ArtifactResult:
    type: ArtifactType = "none"
    raw_content: str = ""
    sanitized_content: str = ""
    security_flags: list[str] = field(default_factory=list)
    is_sanitized: bool = False

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "raw_content": self.raw_content,
            "sanitized_content": self.sanitized_content,
            "security_flags": self.security_flags,
            "is_sanitized": self.is_sanitized,
        }


# ── Public API ────────────────────────────────────────────────────────────────

def extract_artifact(response_text: str) -> ArtifactResult:
    """
    Inspect an LLM response for embedded HTML or Markdown artifacts.

    Priority order:
      1. Fenced HTML block  → type="html"
      2. Fenced Markdown block → type="markdown"
      3. Response starts with an HTML doctype / tag → type="html"
      4. Response is predominantly Markdown headings → type="markdown"
      5. Otherwise → type="none"

    Returns an ArtifactResult with sanitized content and security metadata.
    """
    # 1. Fenced HTML block
    html_match = _FENCED_HTML_RE.search(response_text)
    if html_match:
        raw = html_match.group(1)
        return _build_html_result(raw)

    # 2. Fenced Markdown block
    md_match = _FENCED_MD_RE.search(response_text)
    if md_match:
        raw = md_match.group(1)
        return ArtifactResult(
            type="markdown",
            raw_content=raw,
            sanitized_content=raw,  # Markdown is safe; sanitized by renderer
            security_flags=[],
            is_sanitized=False,
        )

    # 3. Response body looks like HTML
    stripped = response_text.strip()
    if _looks_like_html(stripped):
        return _build_html_result(stripped)

    # 4. Response body looks like rich Markdown
    if _looks_like_rich_markdown(stripped):
        return ArtifactResult(
            type="markdown",
            raw_content=stripped,
            sanitized_content=stripped,
            security_flags=[],
            is_sanitized=False,
        )

    return ArtifactResult(type="none")


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _looks_like_html(text: str) -> bool:
    """Heuristic: starts with an HTML doctype or opening tag."""
    lower = text[:200].lower().strip()
    return lower.startswith("<!doctype") or lower.startswith("<html") or (
        lower.startswith("<") and any(
            tag in lower for tag in ["<div", "<section", "<article", "<main", "<p "]
        )
    )


def _looks_like_rich_markdown(text: str) -> bool:
    """Heuristic: contains multiple Markdown heading lines."""
    heading_count = sum(1 for line in text.splitlines() if line.startswith("#"))
    return heading_count >= 2


def _build_html_result(raw_html: str) -> ArtifactResult:
    """Sanitize raw HTML and build an ArtifactResult."""
    flags: list[str] = []
    sanitized = raw_html

    if _SCRIPT_TAG_RE.search(sanitized):
        flags.append("SCRIPT_TAG_REMOVED")
        sanitized = _SCRIPT_TAG_RE.sub("<!-- [script removed] -->", sanitized)

    if _INLINE_EVENT_RE.search(sanitized):
        flags.append("INLINE_EVENT_HANDLER_REMOVED")
        sanitized = _INLINE_EVENT_RE.sub("", sanitized)

    if _JAVASCRIPT_HREF_RE.search(sanitized):
        flags.append("JAVASCRIPT_HREF_REMOVED")
        sanitized = _JAVASCRIPT_HREF_RE.sub('href="#"', sanitized)

    if _IFRAME_RE.search(sanitized):
        flags.append("IFRAME_REMOVED")
        sanitized = _IFRAME_RE.sub("<!-- [iframe removed] -->", sanitized)

    if _OBJECT_EMBED_RE.search(sanitized):
        flags.append("EMBED_REMOVED")
        sanitized = _OBJECT_EMBED_RE.sub("<!-- [embed removed] -->", sanitized)

    return ArtifactResult(
        type="html",
        raw_content=raw_html,
        sanitized_content=sanitized,
        security_flags=flags,
        is_sanitized=len(flags) > 0,
    )
