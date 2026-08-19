"""Hybrid retrieval: BM25 + vector search, fused with RRF, then cross-encoder rerank."""
import numpy as np
from rank_bm25 import BM25Okapi

from config import get_embedder, get_reranker
from db import get_connection, release_connection
from utils import reciprocal_rank_fusion


def fetch_all_chunks() -> list:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content FROM document_sections;")
            return cur.fetchall()
    finally:
        release_connection(conn)


def bm25_search(query: str, all_chunks: list, top_k: int = 10) -> list:
    contents = [chunk[1] for chunk in all_chunks]
    if not contents:
        return []
    tokenized_corpus = [doc.lower().split() for doc in contents]
    tokenized_query = query.lower().split()
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        (all_chunks[i][0], all_chunks[i][1], float(scores[i])) for i in top_indices
    ]


def vector_search(query: str, top_k: int = 10) -> list:
    query_embedding = get_embedder().encode(query).tolist()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, 1 - (embedding <=> %s::vector) AS similarity
                FROM document_sections
                ORDER BY similarity DESC
                LIMIT %s;
                """,
                (query_embedding, top_k),
            )
            return cur.fetchall()
    finally:
        release_connection(conn)


def rerank(query: str, candidates: list, top_k: int = 3) -> list:
    if not candidates:
        return []
    pairs = [(query, content) for _, content, _ in candidates]
    scores = get_reranker().predict(pairs)
    scored = [
        (candidates[i][0], candidates[i][1], float(scores[i]))
        for i in range(len(candidates))
    ]
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]


def retrieve_chunks(query: str, top_k: int = 5) -> list:
    """Return [(content, score), ...] fused and reranked."""
    all_chunks = fetch_all_chunks()
    if not all_chunks:
        return []
    bm25_results = bm25_search(query, all_chunks, top_k=10)
    vector_results = vector_search(query, top_k=10)
    fused = reciprocal_rank_fusion(bm25_results, vector_results)
    reranked = rerank(query, fused[:20], top_k=top_k)
    return [(content, score) for _, content, score in reranked]
