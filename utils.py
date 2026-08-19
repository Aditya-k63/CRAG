"""Pure helper functions with no heavy imports (safe for unit testing)."""
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 600
CHUNK_OVERLAP = 50


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return splitter.split_text(text)


def cosine_similarity(a, b) -> float:
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def reciprocal_rank_fusion(
    bm25_results: list, vector_results: list, k: int = 60
) -> list:
    """Combine two ranked result lists via Reciprocal Rank Fusion (RRF)."""
    fused_scores: dict = {}
    contents_map: dict = {}
    for rank, (doc_id, content, _score) in enumerate(bm25_results):
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        contents_map[doc_id] = content
    for rank, (doc_id, content, _score) in enumerate(vector_results):
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        contents_map[doc_id] = content
    sorted_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)
    return [
        (doc_id, contents_map[doc_id], fused_scores[doc_id])
        for doc_id in sorted_ids
    ]
