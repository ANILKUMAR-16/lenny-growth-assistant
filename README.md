# 🚀 Lenny Growth Assistant

> An AI-powered growth advisor grounded in Lenny Rachitsky's podcast transcripts. Ask growth questions, generate Ship 30 essays, and explore product strategy.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![pgvector](https://img.shields.io/badge/pgvector-0.3-336791?logo=postgresql)](https://github.com/pgvector/pgvector)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38BDF8?logo=tailwindcss)](https://tailwindcss.com)

---

## ✨ Features

| Feature                    | Description                                                                   |
| -------------------------- | ----------------------------------------------------------------------------- |
| 🔍 **RAG Chat**            | Ask questions grounded in Lenny's podcast transcripts, with source references |
| 🔀 **Model Toggle**        | Switch between local Ollama (`llama3.2`) and supported cloud models           |
| ✍️ **Ship 30 Skill**       | Generate structured, long-form essays from growth topics                      |
| 📄 **Artifact Viewer**     | View Markdown content and preview HTML in a sandboxed environment             |
| 🛡 **Security Badge**      | HTML sanitization with XSS detection and flag reporting                       |
| 💾 **Session Persistence** | Store conversation history in PostgreSQL                                      |
| 📊 **Citation Engine**     | Use pgvector similarity search to retrieve relevant transcript passages       |

---

## 🏗 Architecture

```text
Frontend (React / Vite / Tailwind CSS)
                 │
                 ▼
Backend (FastAPI / Python)
                 │
          ┌──────┴──────┐
          ▼             ▼
   PostgreSQL       LLM Router
   + pgvector           │
                  ┌─────┴─────┐
                  ▼           ▼
               Ollama    Cloud Models
                         (if configured)
```

See [`docs/architecture.md`](docs/architecture.md) for more details.

---

## ⚡ Quick Start — Docker Compose

### Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
* [Ollama](https://ollama.com/) for local model inference, if using a local model

### 1. Clone and configure

Clone this repository, navigate into the project directory, and copy the environment template:

```bash
cp .env.example .env
```

Edit `.env` and configure your preferred model provider:

```env
MODEL_PROVIDER=ollama
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

Add the appropriate API key only if you choose a supported cloud provider.

### 2. Set up Ollama (optional)

Install Ollama, then run:

```bash
ollama serve
ollama pull llama3.2
```

The model download is approximately 2 GB.

### 3. Start the application

```bash
docker-compose up --build
```

This starts the configured services:

1. PostgreSQL with the pgvector extension
2. The FastAPI backend
3. The React frontend served through Nginx

The first startup may take several minutes while dependencies and the embedding model are prepared.

### 4. Load the transcript data

Once the backend is running, send a request to the ingestion endpoint:

```bash
curl -X POST http://localhost:8000/ingest
```

### 5. Open the application

| Service               | URL                          |
| --------------------- | ---------------------------- |
| **Frontend**          | http://localhost:3000        |
| **API Documentation** | http://localhost:8000/docs   |
| **Health Check**      | http://localhost:8000/health |

---

## 🛠 Local Development

### Backend

```bash
cd backend
python -m venv .venv
```

Activate the environment on Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the environment variables using `.env.example`. Make sure the database connection settings match your local PostgreSQL setup.

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend development server is available at:

http://localhost:5173

---

## 🧪 Running Tests

From the backend directory:

```bash
pip install -r requirements.txt
pytest -v
```

To run individual test files:

```bash
pytest tests/test_api.py -v
pytest tests/test_rag.py -v
```

To run tests with coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

The test suite is configured to use an in-memory SQLite database and mocked LLM calls where supported, so tests may not require a live PostgreSQL instance or external AI service.

---

## 📁 Project Structure

```text
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── rag.py
│   │   ├── artifact.py
│   │   └── skills/
│   │       └── ship30.py
│   ├── tests/
│   │   ├── test_api.py
│   │   └── test_rag.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   └── ArtifactViewer.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   └── design.md
├── data/
│   └── sample_transcripts.json
├── transcripts/
│   └── README.md
├── docker-compose.yml
├── .env.example
├── pytest.ini
└── README.md
```

---

## 🔌 API Reference

### `GET /health`

Checks application and configured service connectivity.

### `POST /chat`

Accepts a question and returns an AI-generated answer using relevant transcript information.

Example request:

```json
{
  "message": "How did Airbnb achieve product-market fit?",
  "session_id": "optional-uuid",
  "model_provider": "ollama",
  "top_k": 5
}
```

### `POST /skills/ship30`

Generates a structured essay based on a growth topic and relevant transcript information.

Example request:

```json
{
  "topic": "How referral programs create compounding growth",
  "model_provider": "ollama",
  "top_k": 5
}
```

### `POST /ingest`

Loads the configured sample transcript data into the vector database. No request body is required.

### `GET /sessions/{session_id}/history`

Retrieves the conversation history associated with a session.

Explore and test these endpoints through the interactive API documentation at `http://localhost:8000/docs`.

---

## 🔒 Security Considerations

* HTML artifacts are sanitized before display.
* HTML previews run inside a sandboxed iframe.
* API keys are configured through environment variables rather than hardcoded in application code.
* Cross-origin requests are restricted to configured origins.

---

## 📝 License

MIT © 2026 Oogway Labs
