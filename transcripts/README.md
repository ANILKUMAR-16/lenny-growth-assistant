# Coding Agent Transcript Logging

This directory holds structured logs of coding agent sessions for audit, debugging, and continuous improvement purposes.

## Directory Structure

```
transcripts/
├── README.md              ← You are here
├── schema.json            ← JSON schema for transcript objects
└── sessions/
    └── <session-id>.json  ← Per-session transcript files
```

## Transcript Schema

Each transcript file is a JSON object with the following shape:

```json
{
  "schema_version": "1.0",
  "session_id": "uuid-v4",
  "created_at": "ISO-8601 timestamp",
  "agent": "lenny-growth-assistant",
  "model_provider": "ollama | anthropic | openai",
  "model_name": "llama3.2 | claude-3-5-sonnet-20241022 | gpt-4o",
  "turns": [
    {
      "turn_index": 0,
      "role": "user | assistant",
      "content": "Message text",
      "timestamp": "ISO-8601 timestamp",
      "metadata": {
        "rag_chunks_retrieved": 5,
        "citations": [
          {
            "transcript_title": "How Airbnb Achieved Product-Market Fit",
            "source_url": "https://...",
            "chunk_index": 2,
            "similarity_score": 0.89
          }
        ],
        "artifact_detected": true,
        "artifact_type": "markdown | html",
        "skill_triggered": "ship30 | null",
        "latency_ms": 1423
      }
    }
  ],
  "summary": {
    "total_turns": 12,
    "skills_triggered": ["ship30"],
    "avg_latency_ms": 980,
    "artifacts_generated": 2
  }
}
```

## Logging Behavior

- Transcripts are appended per-turn as the session progresses.
- Each file is named `<session-id>.json` and stored in `transcripts/sessions/`.
- The backend `/chat` endpoint writes to the transcript log after each assistant response.
- Transcripts are **not** used for RAG retrieval — they are audit logs only.

## Retention Policy

| Environment | Retention |
|-------------|-----------|
| Development | 7 days    |
| Staging     | 30 days   |
| Production  | 90 days   |

## Privacy

All transcript content is stored on your infrastructure. No data is sent to external logging services. API keys and secrets are never logged.
