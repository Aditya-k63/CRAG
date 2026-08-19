# CRAG — Corrective Retrieval-Augmented Generation Stack

An end-to-end RAG system combining **LangGraph** agent orchestration with **Groq**'s inference engine for fast, context-aware question answering over your own documents. Built as a single deployable unit — a FastAPI backend that serves both the API and a ChatGPT-style chat UI, backed by a pgvector knowledge store — designed to run comfortably on free-tier cloud hosting.

## Why this exists

Most RAG demos assume a multi-service setup with generous hosting budgets. CRAG is built the opposite way: everything — ingestion, embedding, retrieval, agent reasoning, and UI — runs inside **one container**, so it deploys cleanly on single-port platforms like Render's free tier without sacrificing the LangGraph agent architecture underneath.

## The corrective flow (how the agent decides)

```text
User query
   │
   ▼
retrieve ──▶ hybrid search (BM25 + pgvector + RRF + cross-encoder rerank)
   │
   ▼
evaluate ──▶ Groq grades the retrieved chunks ("yes" / "no")
   │
   ├─ "yes" ────────────────────────────────▶ generate
   │                                           │
   └─ "no" ──▶ web_fallback (DuckDuckGo) ──▶ generate
                                               │
                                               ▼
                                         final answer
```

The **correction** is the differentiator: if the local knowledge base doesn't actually answer the query, the agent detects it and falls back to web search instead of hallucinating from irrelevant context.

## Features

- **Agentic retrieval** via LangGraph — queries are routed through an agent graph that reasons about *how* to answer, not just fetch-and-stuff context.
- **Hybrid retrieval** — BM25 + pgvector results fused with Reciprocal Rank Fusion, then cross-encoder reranking.
- **Local embeddings** with `sentence-transformers` — no external embedding API calls.
- **PDF ingestion** — upload via the UI, text is extracted, chunked, and embedded straight into the vector store.
- **pgvector-backed search** on PostgreSQL — structured, queryable, production-friendly.
- **Groq inference** for low-latency LLM responses inside the agent loop.
- **ChatGPT-style chat UI** — dark theme, conversation history, PDF attach, model selector, voice input.
- **Single-container deployment** — one Dockerfile, one exposed port, everything behind one FastAPI process.

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM inference | Groq |
| Backend API | FastAPI + Uvicorn |
| Frontend | Static HTML/CSS/JS chat UI (served by FastAPI) |
| Vector storage | PostgreSQL + pgvector |
| Embeddings / reranker | sentence-transformers (local) |
| Hybrid retrieval | BM25 (rank-bm25) + RRF |
| PDF parsing | pypdf |
| Deployment | Docker (unified single-service build) |

## Repository Layout

```text
CRAG/
├── .github/workflows/build-pipeline.yml   # CI: lint, unit tests, Docker build/push
├── Dockerfile                             # Unified single-service build recipe
├── start.sh                               # Container entrypoint (honors $PORT)
├── frontend/                              # ChatGPT-style chat UI (HTML/CSS/JS)
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── config.py                              # Env settings + lazy-loaded models
├── db.py                                  # Lazy connection pool + schema bootstrap
├── utils.py                               # Pure helpers (chunking, fusion, cosine)
├── retrieval.py                           # Hybrid retrieval pipeline
├── metrics.py                             # Faithfulness / relevance / precision
├── rag_query.py                           # LangGraph CRAG agent
├── main.py                                # FastAPI app (API + serves the UI)
├── ingestion.py                           # Schema init + batch ingestion
├── evaluate.py                            # RAG accuracy evaluation script
├── requirements.txt
└── tests/                                 # Unit tests (pure logic, no DB needed)
```

## Getting Started

### Prerequisites

- Python 3.11
- Docker + Docker Compose (easiest path) **or** a PostgreSQL instance with the `pgvector` extension

### Option A — Docker Compose (recommended)

```powershell
copy .env.example .env     # then fill in GROQ_API_KEY
docker compose up --build
```

- Chat UI → `http://localhost:8000`
- FastAPI Swagger docs → `http://localhost:8000/docs`

The DB schema is created automatically on app startup — no manual migration step.

### Option B — Run locally

1. Start a PostgreSQL instance with pgvector enabled.
2. Create a `.env` file from `.env.example`:

```env
GROQ_API_KEY=your_groq_api_key_here
API_KEY=rag-secret-2026
DB_NAME=crag_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

3. Install and run:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open `http://localhost:8000` to chat with your documents.

## API

All endpoints except `/` and `/health` require the `X-API-Key` header.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | DB connectivity + cache size |
| GET | `/documents` | List ingested PDFs and their chunk counts |
| POST | `/query` | Ask a question through the CRAG agent (`{"question", "top_k", "model"}`) |
| POST | `/evaluate-query` | Query + RAG quality metrics, logged to `rag_evaluations` |
| POST | `/upload` | Ingest a PDF (multipart `file`, optional `?force=true`) |
| POST | `/cache/clear` | Clear the in-memory query cache |

## Evaluation

```powershell
python evaluate.py
```

Scores faithfulness (hallucination check), answer relevance, and context precision on a fixed test set, then logs every run to the `rag_evaluations` table so you can track regressions over time.

## Roadmap

- [ ] Multi-document conversational memory
- [ ] Authentication for production deployments
- [ ] Streaming responses from the agent graph

## License

Add your license of choice here (MIT is a common default for open-source projects).