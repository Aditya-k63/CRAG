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
you may have got the basic idea what i have made


Grasped core concept, anticipated next direction
Grasped core concept, anticipated next direction
Yeah, I've got the full picture. It's a RAG system with:

LangGraph orchestrating the agent logic, using Groq for fast inference
FastAPI backend doing ingestion (PDF parsing via pdfplumber), local embedding generation (sentence-transformers), and vector search against PostgreSQL + pgvector
Streamlit frontend as the chat/search UI, talking to the API internally
Both services bundled into one Docker container (via run.py running them concurrently) specifically so it fits Render's single-port free-tier constraint — that's a smart workaround since Render's free tier only exposes one port
Solid architecture — self-hosted embeddings keep costs down, Groq keeps latency low, and the unified container sidesteps the multi-service deployment headache you'd otherwise hit on a free hosting tier.

Is this the Hybrid RAG project from your resume, or a separate one? If it's tied to your resume, I can help you add the GitHub/live demo link once it's deployed — or if you want, I can help write a shorter project blurb version of this for your resume/portfolio page (the README is great for GitHub but way too long for a resume bullet).

now you write one read me for me


Sought clarification on project specification
Sought clarification on project specification
Sure — which project do you want the README for? I know you've got a few on your plate:

STGCN Traffic Speed Forecasting
Crypto Direction Predictor
Queue-based Agentic AI system (FastAPI/Redis/Celery/LangChain ReAct)
Something else entirely (maybe a new one, or this CRAG project reframed as your own)
And if you can share a quick rundown of the tech stack, folder structure, and how to run it (or just paste in your code/file list), I'll write it in the same clean style as the last one.

this project only


Devised original README framework for project documentation
Devised original README framework for project documentation
Got it — writing this one myself, same project (the CRAG stack), in my own words with a bit more polish and structure. I'll use everything I know about it from your doc.


Created a file, read a file
Created a file, read a file
Added a proper architecture diagram, tech stack table, and a roadmap section on top of the setup/deploy stuff — makes it feel less like a copy-paste doc and more like a real project page.

A few things I filled in with reasonable guesses since I don't have your actual repo details:

License — left as a placeholder, add whichever you're using (or none)
Roadmap items — made these up as plausible next steps, edit or delete freely
Architecture diagram — ASCII, so it renders fine on GitHub without needing an image
If you've got a live demo link, GitHub repo URL, or screenshots you want in there, send them over and I'll drop them in.


Readme original
Document · MD 
can you not wt=riet ein complete md file whaere i can just copy and paste


Determined to provide copyable markdown content directly
Determined to provide copyable markdown content directly
The user needs the markdown as plain text they can copy directly from the chat, so I'll provide the full README content in a code block for easy copying.

Done
Totally — here's the whole thing as plain text, ready to copy-paste directly into your README.md:

markdown
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
┌─────────────────────────────────────────────┐
│ Docker Container │
│ │
│ ┌───────────────┐ ┌──────────────┐ │
│ │ Streamlit UI │──────▶│ FastAPI │ │
│ │ (port 10000) │◀──────│ (port 8000) │ │
│ └───────────────┘ └───────┬──────┘ │
│ │ │
│ ┌──────────▼───────┐ │
│ │ LangGraph Agent │ │
│ │ + Groq LLM │ │
│ └──────────┬───────┘ │
│ │ │
│ ┌──────────▼───────┐ │
│ │ PostgreSQL + │ │
│ │ pgvector store │ │
│ └──────────────────┘ │
└─────────────────────────────────────────────┘


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
CRAG/
├── .github/
│ └── workflows/
│ └── build-pipeline.yml # CI/CD linting and validation
├── Dockerfile # Unified multi-service build recipe
├── app.py # Streamlit UI
├── docker-compose.yml # Local container orchestration
├── evaluate.py # RAG accuracy evaluation scripts
├── ingestion.py # PDF processing and chunking pipeline
├── main.py # FastAPI app + LangGraph agent setup
├── rag_query.py # Vector search and context compilation
├── requirements.txt # Python dependencies
└── run.py # Concurrent process runner


## Getting Started

### Prerequisites

- Python 3.11
- A running PostgreSQL instance with the `pgvector` extension enabled

### 1. Configure environment variables

Create a `.env` file in the project root:
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/crag_db


### 2. Install dependencies
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt


### 3. Run locally
python run.py


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
