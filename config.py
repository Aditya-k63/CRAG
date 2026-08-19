"""Centralized configuration and lazily-loaded ML models.

Loading sentence-transformers models at import time slows startup and can
crash the process when a dependency is missing or a download fails. Everything
here is lazy: models are built on first use and cached for the process lifetime.
"""
import os

from dotenv import load_dotenv
from sentence_transformers import CrossEncoder, SentenceTransformer

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "groq/compound-mini")

_embedder: SentenceTransformer | None = None
_reranker: CrossEncoder | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker
