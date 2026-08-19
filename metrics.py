"""RAG quality metrics shared by the API and the evaluation script."""
from config import get_embedder
from utils import cosine_similarity

NO_INFO_PHRASES = [
    "i don't have enough information",
    "i cannot answer",
    "not in the context",
]


def compute_faithfulness(answer: str, chunks: list[str]) -> float:
    if any(phrase in answer.lower() for phrase in NO_INFO_PHRASES):
        return 1.0
    context = " ".join(chunks)
    return round(
        cosine_similarity(get_embedder().encode(answer), get_embedder().encode(context)),
        4,
    )


def compute_answer_relevance(question: str, answer: str) -> float:
    return round(
        cosine_similarity(get_embedder().encode(question), get_embedder().encode(answer)),
        4,
    )


def compute_context_precision(
    question: str, chunks: list[str], threshold: float = 0.4
) -> float:
    q_emb = get_embedder().encode(question)
    relevant = sum(
        1
        for chunk in chunks
        if cosine_similarity(q_emb, get_embedder().encode(chunk)) >= threshold
    )
    return round(relevant / len(chunks), 4) if chunks else 0.0


def evaluate(question: str, answer: str, chunks: list[str]) -> dict:
    faithfulness = compute_faithfulness(answer, chunks)
    relevance = compute_answer_relevance(question, answer)
    precision = compute_context_precision(question, chunks)
    overall = round((faithfulness * 0.4) + (relevance * 0.4) + (precision * 0.2), 4)
    return {
        "faithfulness": faithfulness,
        "answer_relevance": relevance,
        "context_precision": precision,
        "overall_score": overall,
    }
