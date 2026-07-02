Contextual Retrieval-Augmented Generation (CRAG) Stack

This repository contains a full-stack, AI-driven Retrieval-Augmented Generation (RAG) system utilizing LangGraph and the Groq inference engine. The application features a Python FastAPI backend acting as the core agentic service, integrated with a PostgreSQL and pgvector database for managing structured knowledge embeddings. The frontend is powered by a Streamlit interface, providing an accessible web dashboard for real-time semantic search and agent query execution.

Both the backend and frontend services are consolidated into a unified architectural layout, allowing the entire stack to build and run inside a single containerized environment tailored for simple cloud hosting deployments like Render.

System Architecture

The application operates as a single unified service. When the container initializes, a primary process manager launches the FastAPI backend and the Streamlit frontend concurrently:


Backend Services: Hosted internally via Uvicorn on port 8000. It manages ingestion, document text extraction via pdfplumber, local text vectorization using sentence-transformers, and routing through LangGraph agents.
Frontend Services: Hosted on port 10000. It reads user prompts, forwards them internally to the localhost API endpoint, and renders the agent's graph processing steps and final semantic responses to the browser.


Repository Layout

textCRAG/
├── .github/
│   └── workflows/
│       └── build-pipeline.yml   # CI/CD automated linting and validation pipeline
├── Dockerfile                  # Unified Docker multi-service build recipe
├── app.py                      # Streamlit UI implementation 
├── docker-compose.yml          # Local container orchestration matrix
├── evaluate.py                 # RAG accuracy evaluation scripts
├── ingestion.py                # PDF processing and text split pipeline
├── main.py                     # FastAPI application layer and LangGraph agent setups
├── rag_query.py                # Vector search operations and context compilation
├── requirements.txt            # System dependency declarations
└── run.py                      # Parallel execution process manager script

Setup and Installation

Local Prerequisites

Ensure you have Python 3.11 installed along with a running PostgreSQL instance configured with the pgvector extension.

1. Environment Configuration

Create a file named .env in the root directory and define the following variables:

envGROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/crag_db

2. Local Environment Setup

Initialize a clean virtual environment and install the required library dependencies:

powershellpython -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

3. Running the Stack Locally

To start both the backend API and frontend interface simultaneously using the process runner, execute:

powershellpython run.py


The Streamlit interface will be available at: http://localhost:10000
The FastAPI documentation swagger will be accessible at: http://localhost:8000/docs


Production Deployment on Render

This repository is optimized to deploy directly onto Render's Web Service platform using the unified Docker architecture, which operates within Render's single-port routing limitations.


Create a new Web Service on the Render Dashboard and link this GitHub repository.
Configure the following runtime variables on the setup panel:

Runtime: Docker
Instance Type: Free



Add your required production keys under the Environment Variables submenu:

GROQ_API_KEY
DATABASE_URL (Pointing to your managed production PostgreSQL/pgvector database)



Deploy the service. Render will parse the root Dockerfile, trigger the unified build process, expose port 10000 automatically, and launch the service cluster using run.py.
