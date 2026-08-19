"""Unit tests for the pure helper functions (no DB / ML model required)."""
import numpy as np
import pytest

from utils import chunk_text, cosine_similarity, reciprocal_rank_fusion


class TestChunkText:
    def test_splits_long_text_into_chunks(self):
        text = "word " * 3000
        chunks = chunk_text(text, chunk_size=600, chunk_overlap=50)
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        assert all(isinstance(c, str) and c for c in chunks)

    def test_short_text_stays_single_chunk(self):
        chunks = chunk_text("hello world", chunk_size=600, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == "hello world"

    def test_empty_text_returns_empty(self):
        assert chunk_text("") == []


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
        assert cosine_similarity([1.0, 0.0], [0.0, 0.0]) == 0.0

    def test_returns_float(self):
        assert isinstance(cosine_similarity([1.0], [2.0]), float)


class TestReciprocalRankFusion:
    def test_combines_and_ranks_by_fused_score(self):
        bm25 = [(1, "a", 5.0), (2, "b", 4.0)]
        vector = [(2, "b", 0.9), (3, "c", 0.8)]
        fused = reciprocal_rank_fusion(bm25, vector)
        ids = [doc_id for doc_id, _, _ in fused]
        assert ids == [2, 1, 3]  # shared doc (2) gets the highest fused score

    def test_scores_are_descending(self):
        bm25 = [(1, "a", 1.0), (2, "b", 1.0), (3, "c", 1.0)]
        vector = [(4, "d", 1.0)]
        fused = reciprocal_rank_fusion(bm25, vector)
        scores = [score for _, _, score in fused]
        assert scores == sorted(scores, reverse=True)
        assert all(isinstance(s, float) for s in scores)

    def test_empty_inputs(self):
        assert reciprocal_rank_fusion([], []) == []