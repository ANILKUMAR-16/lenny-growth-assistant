# 🚀 Lenny Growth Assistant

> An AI-powered growth advisor grounded in Lenny Rachitsky's podcast transcripts.
> Built by **Oogway Labs** — ask growth questions, generate Ship 30 essays, and explore product strategy.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![pgvector](https://img.shields.io/badge/pgvector-0.3-336791?logo=postgresql)](https://github.com/pgvector/pgvector)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38BDF8?logo=tailwindcss)](https://tailwindcss.com)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **RAG Chat** | Ask questions grounded in Lenny's podcast transcripts with inline citations |
| 🔀 **Model Toggle** | Switch between local Ollama (🦙 llama3.2) and cloud Claude / GPT-4o |
| ✍️ **Ship 30 Skill** | Generate ~1,250-word structured essays from any growth topic |
| 📄 **Artifact Viewer** | Side-by-side Markdown renderer + sandboxed HTML preview |
| 🛡 **Security Badge** | HTML sanitization with XSS detection and transparent flag reporting |
| 💾 **Session Persistence** | Full conversation history stored in PostgreSQL |
| 📊 **Citation Engine** | pgvector cosine similarity with source URLs and confidence scores |

---

## 🏗 Architecture

```
frontend (React/Vite/Tailwind) ──► backend (FastAPI/Python)
                                          │
                                    ┌─────┴──────┐
                                PostgreSQL      LLM Router
                               (pgvector)    ┌───┴───────┐
                                            Ollama  Anthropic/OpenAI
```

See [`docs/architecture.md`](docs/architecture.md) for full details.

---

## ⚡ Quick Start — Docker Compose (Recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- *(Optional)* [Ollama](https://ollama.ai) for local model inference

### 1. Clone & Configure

```bash
# Copy environment template
cp .env.example .env
```

Edit `.env` with your preferred settings:
```env
MODEL_PROVIDER=ollama          # or: anthropic / openai
ANTHROPIC_API_KEY=sk-ant-...   # if using Anthropic
OPENAI_API_KEY=sk-...          # if using OpenAI
```

### 2. (Optional) Set up Ollama locally

```bash
# Install Ollama from https://ollama.ai
ollama serve                   # start the server
ollama pull llama3.2           # download the model (~2GB)
```

### 3. Start all services

```bash
docker-compose up --build
```

This will:
1. Start PostgreSQL with pgvector extension
2. Build and start the FastAPI backend (includes embedding model download ~85MB)
3. Build and start the React frontend via nginx

**First startup takes 3–5 minutes** due to embedding model download.

### 4. Seed the knowledge base

```bash
curl -X POST http://localhost:8000/ingest
```

### 5. Open the app

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

---

## 🛠 Local Development (Without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp ../.env.example .env
# Edit .env with your DATABASE_URL pointing to a local Postgres

# Run dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api → localhost:8000)
npm run dev
```

Frontend available at: http://localhost:5173

---

## 🧪 Running Tests

```bash
cd backend

# Install test dependencies (included in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_api.py -v
pytest tests/test_rag.py -v

# Run with coverage
pytest --cov=app --cov-report=term-missing
```

Tests use:
- **SQLite in-memory** (no live Postgres required)
- **Mocked LLM calls** (no Ollama or API keys required)
- `pytest-asyncio` for async test support

---

## 📁 Project Structure

```
Oogway/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app & endpoints
│   │   ├── config.py        # Pydantic settings
│   │   ├── db.py            # PostgreSQL + pgvector models
│   │   ├── rag.py           # Embeddings, retrieval, LLM router
│   │   ├── artifact.py      # HTML/Markdown detection & sanitization
│   │   └── skills/
│   │       └── ship30.py    # Ship 30 for 30 essay skill
│   ├── tests/
│   │   ├── test_api.py      # API integration tests
│   │   └── test_rag.py      # RAG unit tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx   # Chat UI + model toggle
│   │   │   └── ArtifactViewer.jsx  # Markdown & sandboxed HTML viewer
│   │   ├── App.jsx          # Root layout
│   │   ├── main.jsx         # React entry point
│   │   └── index.css        # Global styles (Tailwind + custom)
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── docs/
│   ├── PRD.md               # Product requirements
│   ├── architecture.md      # System design
│   └── design.md            # UI/UX spec
├── data/
│   └── sample_transcripts.json  # Lenny podcast transcript data
├── transcripts/
│   └── README.md            # Transcript logging schema
├── docker-compose.yml
├── .env.example
├── pytest.ini
└── README.md
```

---

## 🔌 API Reference

### `GET /health`
Check database and Ollama connectivity.

### `POST /chat`
```json
{
  "message": "How did Airbnb achieve product-market fit?",
  "session_id": "optional-uuid",
  "model_provider": "ollama",
  "top_k": 5
}
```

### `POST /skills/ship30`
```json
{
  "topic": "How referral programs create compounding growth",
  "model_provider": "anthropic",
  "top_k": 5
}
```

### `POST /ingest`
Seeds `data/sample_transcripts.json` into pgvector. No body required.

### `GET /sessions/{session_id}/history`
Returns full message history for a session.

---

## 🔒 Security Notes

- HTML artifacts are sanitized (script tags, event handlers, iframes removed) before display
- Frontend renders HTML in a sandboxed `<iframe sandbox="allow-scripts">` with no parent DOM access
- API keys are loaded from environment variables only — never hardcoded or logged
- CORS is restricted to configured origins

---

## 📝 License

MIT © 2026 Oogway Labs
