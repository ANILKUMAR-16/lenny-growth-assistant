# Architecture Document
## The Lenny Growth Assistant
### Version 1.0 · Oogway Labs

---

## 1. System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Docker Compose                              │
│                                                                      │
│  ┌─────────────┐    ┌──────────────────────┐    ┌────────────────┐  │
│  │  PostgreSQL │    │    FastAPI Backend    │    │  React Frontend│  │
│  │  + pgvector │◄──►│  (uvicorn, port 8000)│◄──►│  (nginx, :3000)│  │
│  │  (port 5432)│    │                      │    │                │  │
│  └─────────────┘    └──────────┬───────────┘    └────────────────┘  │
│                                │                                     │
│                    ┌───────────┴────────────┐                        │
│                    │   LLM Provider Router   │                        │
│                    ├───────────┬────────────┤                        │
│                    │  Ollama   │  Anthropic │  OpenAI                │
│                    │ (host:    │  Claude    │  GPT-4o                │
│                    │  11434)   │  (cloud)   │  (cloud)               │
│                    └───────────┴────────────┘                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema

### `sessions`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Session identifier |
| `created_at` | TIMESTAMPTZ | Session start time |
| `user_metadata` | JSONB | Free-form browser/user context |

### `messages`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Message identifier |
| `session_id` | UUID (FK → sessions) | Parent session |
| `role` | VARCHAR(16) | `"user"` or `"assistant"` |
| `content` | TEXT | Message body |
| `citations` | JSONB | Array of `{index, title, url, score}` |
| `created_at` | TIMESTAMPTZ | Message timestamp |

### `transcript_chunks`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Chunk identifier |
| `transcript_title` | VARCHAR(512) | Episode title |
| `chunk_index` | VARCHAR(16) | Timestamp or sequential index |
| `chunk_text` | TEXT | Raw transcript text |
| `embedding` | VECTOR(384) | Sentence-transformers embedding |
| `source_url` | VARCHAR(2048) | Podcast episode URL |
| `created_at` | TIMESTAMPTZ | Ingestion timestamp |

**Unique constraint**: `(transcript_title, chunk_index)` — ensures idempotent re-ingestion.

### pgvector Index
```sql
CREATE INDEX CONCURRENTLY idx_chunks_embedding
ON transcript_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```
*(Applied manually after initial data load for production performance.)*

---

## 3. RAG Pipeline

```
User Query
    │
    ▼
embed_text(query)  ──►  all-MiniLM-L6-v2 (384-dim, local, no API)
    │
    ▼
pgvector cosine similarity search
    │  SELECT ... ORDER BY embedding <=> $vec LIMIT top_k
    ▼
Retrieved chunks (top-k, score ≥ threshold)
    │
    ▼
build_context_prompt()
    │  Injects [Source N] citations into system prompt
    ▼
call_llm(prompt, provider)
    │
    ▼
LLM Response
    │
    ▼
extract_artifact()  ──►  Detect Markdown / HTML blocks
    │
    ▼
Sanitize HTML  ──►  Strip scripts, event handlers, iframes
    │
    ▼
Persist to DB  +  Return to frontend
```

---

## 4. LLM Toggle Workflow

### Provider Selection
1. **Request-level override**: `POST /chat { "model_provider": "anthropic" }`
2. **Environment default**: `MODEL_PROVIDER=ollama` in `.env`

### Ollama (Local)
- Endpoint: `POST {OLLAMA_BASE_URL}/api/generate`
- Model: configurable via `OLLAMA_MODEL` (default: `llama3.2`)
- Timeout: 120s (configurable)
- **Failure handling**:
  - `ConnectError` → HTTP 503 with message: *"Ollama not running. Run `ollama serve` and `ollama pull llama3.2`"*
  - `TimeoutError` → HTTP 503 with timeout hint

### Anthropic Claude
- SDK: `anthropic` Python SDK (async)
- Model: `claude-3-5-sonnet-20241022` (configurable)
- Requires `ANTHROPIC_API_KEY` env var
- Missing key → HTTP 400

### OpenAI
- SDK: `openai` Python SDK (async)
- Model: `gpt-4o` (configurable)
- Requires `OPENAI_API_KEY` env var

---

## 5. Security Architecture

### HTML Artifact Sanitization
Patterns removed before serving to frontend:

| Pattern | Regex | Risk |
|---------|-------|------|
| `<script>` tags | `<\s*script[\s>].*?</\s*script\s*>` | XSS |
| Inline event handlers | `\s+on\w+\s*=\s*["'][^"']*["']` | DOM event hijacking |
| `javascript:` hrefs | `href\s*=\s*["']javascript:[^"']*["']` | JS execution |
| `<iframe>` tags | `<\s*iframe[\s>].*?</\s*iframe\s*>` | Clickjacking |
| `<object>/<embed>` | Full tag match | Plugin execution |

### Frontend Isolation
- HTML artifacts render inside `<iframe sandbox="allow-scripts">`
- `allow-scripts` enables inline JS within the sandbox **but**:
  - No `allow-same-origin` → iframe cannot access parent DOM
  - No `allow-forms` → cannot submit data
  - No `allow-top-navigation` → cannot redirect parent

### API Security
- CORS configured to specific origins only
- No user authentication in v1 (internal use assumed)
- Secrets loaded exclusively from environment variables

---

## 6. Component Hierarchy

```
App.jsx
├── Header Bar (logo, status pill, artifact toggle)
├── ChatInterface.jsx
│   ├── Empty State (suggested prompts)
│   ├── MessageBubble[] (user + assistant)
│   │   ├── CitationBadge[]
│   │   └── Artifact button (opens ArtifactViewer)
│   ├── TypingIndicator
│   ├── Ship30Modal (topic input)
│   └── Input Area
│       ├── Provider Selector Dropdown
│       ├── Ship30 Quick Button
│       └── Send Button
└── ArtifactViewer.jsx
    ├── Header (type badge, tabs, copy, close)
    ├── SecurityBadge (expandable flags)
    ├── WordCountBadge (for markdown)
    ├── Preview Tab
    │   ├── ReactMarkdown (for .md)
    │   └── SandboxedIframe (for .html)
    ├── Source Tab (raw content)
    └── Footer (security explanation)
```

---

## 7. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | DB + Ollama connectivity check |
| `POST` | `/chat` | Main chat with RAG + artifact extraction |
| `POST` | `/skills/ship30` | Ship 30 essay generator |
| `POST` | `/ingest` | Seed transcript data into pgvector |
| `GET` | `/sessions/{id}/history` | Full message history for a session |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc API docs |

---

## 8. Deployment Architecture

### Local Development
```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

### Docker Compose (Production-like)
```
docker-compose up --build
```
- `postgres` → `lenny_network` (internal)
- `backend` → `lenny_network` + port 8000 exposed
- `frontend` (nginx) → `lenny_network` + port 3000 exposed
- Ollama: runs on host, accessed via `host.docker.internal:11434`
