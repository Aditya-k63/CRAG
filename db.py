"""Database access layer.

A lazy thread-safe connection pool and schema bootstrapping so the API can
start even when PostgreSQL is temporarily unavailable (it will simply fail on
the requests that need it instead of crashing the whole process on import).
"""
import logging
import os

from dotenv import load_dotenv
from psycopg2 import pool
from pgvector.psycopg2 import register_vector

load_dotenv()

logger = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS document_sections (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    meta JSONB,
    embedding VECTOR(%(dimension)s)
);
CREATE INDEX IF NOT EXISTS document_sections_hnsw_idx
ON document_sections USING hnsw (embedding vector_cosine_ops);
"""


def _ensure_env() -> None:
    missing = [
        var for var in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
        if not os.getenv(var)
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Add them to your .env file (see .env.example)."
        )


def _get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _ensure_env()
        _pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )
    return _pool


def get_connection():
    conn = _get_pool().getconn()
    register_vector(conn)
    return conn


def release_connection(conn) -> None:
    _get_pool().putconn(conn)


def init_db_schema() -> None:
    """Create the vector extension, table and HNSW index if they don't exist."""
    from config import EMBEDDING_DIMENSION

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(SCHEMA_SQL, {"dimension": EMBEDDING_DIMENSION})
        conn.commit()
        logger.info("Database schema verified/created.")
    finally:
        release_connection(conn)
