# Product Requirements Document
## The Lenny Growth Assistant
### Version 1.0 · Oogway Labs · September 2026

---

## 1. Discovery Brief

### Problem Statement

Growth practitioners and product managers spend hours hunting through podcast notes, Twitter threads, and blog posts to find actionable frameworks from thought leaders. Lenny Rachitsky's podcast is one of the highest-signal sources in the industry, but its content exists in long-form audio—nearly inaccessible for quick reference during product reviews or strategy sessions.

**The Lenny Growth Assistant** solves this by making Lenny's entire podcast corpus conversationally queryable, instantly surfacing citations, and generating polished growth-focused content artifacts on demand.

### Opportunity

| Signal | Data |
|--------|------|
| Lenny's Newsletter subscribers | 600,000+ |
| Podcast episodes published | 350+ |
| Avg episode length | 75–90 min |
| Time to find specific insight (manual) | 20–45 min |
| Time to find insight (this product) | < 10 sec |

---

## 2. User Personas

### Primary: "The Growth PM" — Alex, 32
- **Role**: Senior PM at a Series B SaaS startup
- **Goal**: Find precedent for a referral program decision before tomorrow's OKR review
- **Pain**: Can't remember which episode covers Dropbox's referral mechanics
- **Usage**: Asks the assistant, gets cited answer + Ship 30 essay for the exec deck

### Secondary: "The Startup Founder" — Priya, 28
- **Role**: Solo founder, PLG startup, 2 months post-launch
- **Goal**: Validate her intuition about activation metrics with real data
- **Pain**: Doesn't have time to listen to 90-minute podcast episodes
- **Usage**: Types "What activation metric should I track?" → cited answer in 8 seconds

### Tertiary: "The Growth Writer" — Marcus, 25
- **Role**: Growth content lead at a VC-backed startup
- **Goal**: Produce two thought leadership posts per week
- **Pain**: Writing takes 4 hours per essay
- **Usage**: Uses Ship 30 skill → 1,250-word structured draft in 60 seconds

---

## 3. Success Metrics

### Acquisition
- Week 1: 500 sessions from Oogway Labs internal team + beta users
- Week 4: 2,000 sessions with <5% bounce rate on chat

### Engagement
- **Primary KPI**: % sessions with ≥3 user messages (measures "aha moment")
- Target: 40% of sessions reach 3+ turns within 60 days
- **Secondary KPI**: Ship 30 essays generated per week — Target: 50/week by Day 30

### Retention (7-day)
- Target: 25% of users return within 7 days for a follow-up session

### Quality
- RAG citation accuracy (spot-checked by team): ≥90% cited claims traceable to source
- LLM response latency (Ollama, p95): <8 seconds
- LLM response latency (Claude, p95): <4 seconds

### Technical
- API error rate: <1%
- System uptime: 99.5%

---

## 4. Scope

### In Scope (v1.0)
- ✅ Conversational chat interface with session persistence
- ✅ RAG retrieval from Lenny podcast transcript corpus
- ✅ Citation engine (source + episode + similarity score)
- ✅ Model toggle: Ollama (local) ↔ Anthropic Claude ↔ OpenAI GPT-4o
- ✅ Ship 30 for 30 essay generation (~1,250 words)
- ✅ Artifact viewer (Markdown + sandboxed HTML)
- ✅ Security sanitization for HTML artifacts
- ✅ `/ingest` endpoint for corpus loading
- ✅ Docker Compose one-command deployment

### Out of Scope (v1.0)
- ❌ Audio transcription pipeline (transcripts are pre-processed)
- ❌ User authentication / multi-tenancy
- ❌ Real-time streaming responses
- ❌ Mobile native app
- ❌ Billing / usage metering
- ❌ Social sharing of essays

### Future Roadmap (v2.0)
- Streaming LLM responses (SSE)
- Automatic episode ingestion via RSS + Whisper transcription
- User accounts with saved sessions and essays
- Export to Notion, Substack, Medium
- Embeddable widget for newsletters

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ollama unavailable in prod | Medium | High | Cloud fallback; clear error messaging |
| Transcript data drift / staleness | Low | Medium | `/ingest` endpoint allows re-seeding |
| LLM hallucination in citations | Medium | High | Strict prompt grounding; [Source N] format; similarity threshold filter |
| pgvector performance at scale | Low | Medium | Index tuning; connection pooling; read replicas |
| HTML artifact XSS | Low | High | Regex sanitizer + iframe sandbox |
| API key exposure | Low | Critical | Keys in .env only; never logged; Docker secrets in prod |

---

## 6. Acceptance Criteria

For v1.0 to be considered shippable:
1. `docker-compose up --build` brings all 3 services healthy within 3 minutes
2. `/ingest` successfully seeds 15 transcript chunks into pgvector
3. `/chat` returns citations for growth-related queries 90% of the time
4. `/skills/ship30` returns ≥1,100 word essay within 120 seconds
5. Frontend renders Markdown and HTML artifacts correctly
6. All pytest tests pass with no failures
