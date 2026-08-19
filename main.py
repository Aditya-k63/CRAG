import io
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader

from config import get_embedder, get_reranker
from db import get_connection, init_db_schema, release_connection
from metrics import evaluate
from rag_query import crag_agent
from utils import chunk_text

load_dotenv()

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# --- Query Cache (in-memory, evicts oldest) ---
query_cache: dict = {}
CACHE_MAX_SIZE = 100


def get_cached_answer(question: str, top_k: int):
    key = f"{question.strip().lower()}::{top_k}"
    return query_cache.get(key)


def set_cached_answer(question: str, top_k: int, result: dict):
    key = f"{question.strip().lower()}::{top_k}"
    if len(query_cache) >= CACHE_MAX_SIZE:
        query_cache.pop(next(iter(query_cache)))
    query_cache[key] = result


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db_schema()
        logger.info("Database schema verified/created on startup.")
    except Exception as e:
        logger.error(f"Schema init failed at startup: {e}")
    # Warm up ML models so the first query doesn't block on lazy loading.
    for name, loader in (("embedder", get_embedder), ("reranker", get_reranker)):
        try:
            loader()
            logger.info(f"Warmed up {name}.")
        except Exception as e:
            logger.error(f"Failed to warm up {name}: {e}")
    yield


app = FastAPI(
    title="RAG API",
    description="Corrective Agentic RAG with pgvector + Groq + LangGraph",
    lifespan=lifespan,
)

# Streamlit UI (separate origin) talks to this API from the browser, so CORS is required.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth ---
API_KEY = os.getenv("API_KEY", "rag-secret-2026")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Pass it as header: X-API-Key",
        )
    return key


# --- Constants ---
MAX_FILE_SIZE = 10 * 1024 * 1024


# --- Schemas ---
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    model: Optional[str] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    chunks_used: int
    sources: list = []


class UploadResponse(BaseModel):
    filename: str
    chunks_inserted: int
    message: str


class EvaluatedQueryResponse(BaseModel):
    question: str
    answer: str
    chunks_used: int
    faithfulness: float
    answer_relevance: float
    context_precision: float
    overall_score: float


# --- DB Helpers ---
def is_already_ingested(filename: str) -> bool:
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM document_sections WHERE meta->>'source' = %s",
                (filename,),
            )
            return cur.fetchone()[0] > 0
    finally:
        if conn is not None:
            release_connection(conn)


def insert_chunks(chunks: list, filename: str) -> int:
    conn = None
    inserted = 0
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            for i, chunk in enumerate(chunks):
                try:
                    embedding = get_embedder().encode(chunk).tolist()
                    metadata = {"source": filename, "chunk_index": i}
                    cur.execute(
                        "INSERT INTO document_sections (content, meta, embedding) VALUES (%s, %s, %s)",
                        (chunk, json.dumps(metadata), embedding),
                    )
                    inserted += 1
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to insert chunk {i} from '{filename}': {e}")
                    raise RuntimeError(f"Insert failed at chunk {i}: {e}")
        conn.commit()
        logger.info(f"Successfully inserted {inserted} chunks from '{filename}'")
        return inserted
    finally:
        if conn is not None:
            release_connection(conn)


def log_evaluation(question: str, answer: str, metrics: dict):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_evaluations (
                    id SERIAL PRIMARY KEY,
                    question TEXT,
                    answer TEXT,
                    faithfulness FLOAT,
                    answer_relevance FLOAT,
                    context_precision FLOAT,
                    overall_score FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                INSERT INTO rag_evaluations
                (question, answer, faithfulness, answer_relevance, context_precision, overall_score)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    question,
                    answer,
                    metrics["faithfulness"],
                    metrics["answer_relevance"],
                    metrics["context_precision"],
                    metrics["overall_score"],
                ),
            )
        conn.commit()
    finally:
        if conn is not None:
            release_connection(conn)


# --- PDF Processing ---
def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


# --- Routes ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/health")
def health():
    conn = None
    try:
        conn = get_connection()
        conn.cursor().execute("SELECT 1")
        return {"status": "healthy", "db": "connected", "cache_size": len(query_cache)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")
    finally:
        if conn is not None:
            release_connection(conn)


@app.get("/documents", dependencies=[Depends(verify_api_key)])
def list_documents():
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT meta->>'source' AS source, COUNT(*) AS chunks
                FROM document_sections
                WHERE meta IS NOT NULL
                GROUP BY meta->>'source'
                ORDER BY source;
                """
            )
            rows = cur.fetchall()
        return {"documents": [{"filename": r[0], "chunks": r[1]} for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")
    finally:
        if conn is not None:
            release_connection(conn)


@app.post("/query", response_model=QueryResponse, dependencies=[Depends(verify_api_key)])
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    cached = get_cached_answer(request.question, request.top_k)
    if cached:
        logger.info(f"Cache hit: {request.question}")
        return QueryResponse(**cached)

    logger.info(f"LangGraph Agent receiving query: {request.question}")
    initial_state = {
        "query": request.question,
        "retrieved_chunks": [],
        "evaluation": "",
        "final_answer": "",
        "top_k": request.top_k,
        "model": request.model,
    }

    try:
        graph_output = crag_agent.invoke(initial_state)
    except Exception as e:
        logger.error(f"Agent pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(e)}")

    answer = graph_output["final_answer"]
    chunks_count = len(graph_output["retrieved_chunks"])
    sources = graph_output.get("sources", [])

    result = {
        "question": request.question,
        "answer": answer,
        "chunks_used": chunks_count,
        "sources": sources,
    }
    set_cached_answer(request.question, request.top_k, result)
    return QueryResponse(**result)


@app.post("/upload", response_model=UploadResponse, dependencies=[Depends(verify_api_key)])
def upload_pdf(file: UploadFile = File(...), force: bool = False):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size is 10MB")

    try:
        if is_already_ingested(file.filename) and not force:
            raise HTTPException(
                status_code=409,
                detail=f"'{file.filename}' already ingested. Use ?force=true to re-upload.",
            )

        if force:
            conn = None
            try:
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM document_sections WHERE meta->>'source' = %s",
                        (file.filename,),
                    )
                conn.commit()
                logger.info(f"Force re-upload: deleted old chunks for '{file.filename}'")
            finally:
                if conn is not None:
                    release_connection(conn)

        text = extract_text_from_pdf(contents)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        chunks = chunk_text(text)
        if len(chunks) > 500:
            raise HTTPException(
                status_code=400,
                detail=f"PDF too large — {len(chunks)} chunks, max is 500",
            )

        insert_chunks(chunks, file.filename)
        query_cache.clear()  # Clear cache after new PDF added
        logger.info(f"Upload complete: {file.filename}. Cache cleared.")

        return UploadResponse(
            filename=file.filename,
            chunks_inserted=len(chunks),
            message=f"Successfully ingested '{file.filename}' into the knowledge base",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed for '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post(
    "/evaluate-query",
    response_model=EvaluatedQueryResponse,
    dependencies=[Depends(verify_api_key)],
)
async def evaluate_query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Run the blocking agent pipeline in a thread so the event loop stays responsive.
    import asyncio
    graph_output = await asyncio.to_thread(
        crag_agent.invoke,
        {
            "query": request.question,
            "retrieved_chunks": [],
            "evaluation": "",
            "final_answer": "",
            "top_k": request.top_k,
            "model": request.model,
        },
    )
    answer = graph_output["final_answer"]

    chunks_text = [content for content, _score, _src in graph_output["retrieved_chunks"]]
    metrics = evaluate(request.question, answer, chunks_text)
    log_evaluation(request.question, answer, metrics)

    return EvaluatedQueryResponse(
        question=request.question,
        answer=answer,
        chunks_used=len(graph_output["retrieved_chunks"]),
        **metrics,
    )


@app.post("/cache/clear", dependencies=[Depends(verify_api_key)])
def clear_cache():
    count = len(query_cache)
    query_cache.clear()
    logger.info(f"Cache cleared — {count} entries removed")
    return {"message": f"Cache cleared. {count} entries removed."}
