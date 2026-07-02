# CRAG — Contextual Retrieval-Augmented Generation Stack

An end-to-end RAG system that combines **LangGraph** agent orchestration with **Groq**'s inference engine for fast, context-aware question answering over your own documents. Built as a single deployable unit — FastAPI backend, Streamlit frontend, and a pgvector-backed knowledge store — designed to run comfortably on free-tier cloud hosting.

## Why this exists

Most RAG demos assume you have a multi-service setup (separate frontend, backend, and vector DB deployments) with generous hosting budgets. CRAG is built the opposite way: everything — ingestion, embedding, retrieval, agent reasoning, and UI — runs inside **one container**, so it deploys cleanly on single-port platforms like Render's free tier without sacrificing the LangGraph agent architecture underneath.

## Features

- **Agentic retrieval** via LangGraph — queries are routed through an agent graph rather than a fixed retrieval pipeline, so the system can reason about *how* to answer, not just fetch-and-stuff context.
- **Local embeddings** using `sentence-transformers` — no external embedding API calls, keeping inference costs down.
- **PDF ingestion** with `pdfplumber` for text extraction and chunking straight into the vector store.
- **pgvector-backed search** on PostgreSQL — structured, queryable, and production-friendly compared to a standalone vector DB.
- **Groq inference** for low-latency LLM responses inside the agent loop.
- **Streamlit dashboard** for real-time semantic search and live visibility into the agent's reasoning steps.
- **Single-container deployment** — one Dockerfile, one process manager, one port exposed.

## Architecture

```text
┌─────────────────────────────────────────────┐
│                  Docker Container             │
│                                               │
│   ┌───────────────┐        ┌──────────────┐  │
│   │  Streamlit UI  │──────▶│   FastAPI     │  │
│   │  (port 10000) │◀──────│  (port 8000)  │  │
│   └───────────────┘        └───────┬──────┘  │
│                                     │          │
│                          ┌──────────▼───────┐  │
│                          │  LangGraph Agent │  │
│                          │   + Groq LLM     │  │
│                          └──────────┬───────┘  │
│                                     │          │
│                          ┌──────────▼───────┐  │
│                          │ PostgreSQL +     │  │
│                          │ pgvector store   │  │
│                          └──────────────────┘  │
└─────────────────────────────────────────────┘
```

`run.py` starts both services concurrently on container init. The Streamlit app talks to the FastAPI layer over `localhost`, so nothing leaves the container except the single exposed port.

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM inference | Groq |
| Backend API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Vector storage | PostgreSQL + pgvector |
| Embeddings | sentence-transformers (local) |
| PDF parsing | pdfplumber |
| Deployment | Docker (unified single-service build) |

## Repository Layout

```text
CRAG/
├── .github/
│   └── workflows/
│       └── build-pipeline.yml   # CI/CD linting and validation
├── Dockerfile                   # Unified multi-service build recipe
├── app.py                       # Streamlit UI
├── docker-compose.yml           # Local container orchestration
├── evaluate.py                  # RAG accuracy evaluation scripts
├── ingestion.py                 # PDF processing and chunking pipeline
├── main.py                      # FastAPI app + LangGraph agent setup
├── rag_query.py                 # Vector search and context compilation
├── requirements.txt             # Python dependencies
└── run.py                       # Concurrent process runner
```

## Getting Started

### Prerequisites

- Python 3.11
- A running PostgreSQL instance with the `pgvector` extension enabled

### 1. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/crag_db
```

### 2. Install dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Run locally

```powershell
python run.py
```

- Streamlit UI → `http://localhost:10000`
- FastAPI Swagger docs → `http://localhost:8000/docs`

## Deploying to Render

1. Create a new **Web Service** on Render and connect this repository.
2. Set **Runtime** to `Docker` and pick an instance type (Free tier works).
3. Add environment variables in the Render dashboard:
   - `GROQ_API_KEY`
   - `DATABASE_URL` (your managed PostgreSQL/pgvector connection string)
4. Deploy. Render builds from the root `Dockerfile`, exposes port `10000`, and starts the stack via `run.py`.

## Evaluation

`evaluate.py` includes scripts for measuring retrieval and answer accuracy — useful for tracking regressions as the ingestion pipeline or prompt strategy changes.

## Roadmap

- [ ] Add reranking step before context compilation
- [ ] Support multi-document conversational memory
- [ ] Add authentication for production deployments
- [ ] CI pipeline expansion (currently lint/validate only)

## License

Add your license of choice here (MIT is a common default for open-source projects).
