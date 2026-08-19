"""RAG accuracy evaluation script: runs the LangGraph agent over a fixed set of
questions, scores faithfulness / relevance / context-precision, and logs results
to the `rag_evaluations` table.
"""
import numpy as np

from db import get_connection, release_connection
from metrics import evaluate
from rag_query import crag_agent

# ---- Log to DB ----
def log_evaluation(question: str, answer: str, metrics: dict):
    conn = get_connection()
    try:
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
        release_connection(conn)


# ---- Test Suite ----
TEST_QUESTIONS = [
    "What is a Python list comprehension?",
    "What were the three main reasons for the founding of the Georgia colony?",
    "How does a for loop work in Python?",
    "What is the purpose of the continue statement?",
]


def run_evaluation(top_k: int = 3) -> float:
    all_scores = []

    for question in TEST_QUESTIONS:
        print(f"\nQ: {question}")

        initial_state = {
            "query": question,
            "retrieved_chunks": [],
            "evaluation": "",
            "final_answer": "",
            "top_k": top_k,
        }
        graph_output = crag_agent.invoke(initial_state)

        answer = graph_output["final_answer"]
        chunks_text = [content for content, _score in graph_output["retrieved_chunks"]]

        metrics = evaluate(question, answer, chunks_text)
        log_evaluation(question, answer, metrics)

        print(f"Answer: {answer[:120]}...")
        print(f"  Faithfulness:      {metrics['faithfulness']:.4f}  (hallucination check)")
        print(f"  Answer Relevance:  {metrics['answer_relevance']:.4f}  (addresses question?)")
        print(f"  Context Precision: {metrics['context_precision']:.4f}  (chunks useful?)")
        print(f"  Overall Score:     {metrics['overall_score']:.4f}")

        all_scores.append(metrics["overall_score"])

    avg = float(np.mean(all_scores))
    print("\n" + "=" * 60)
    print(f"AVERAGE AGENT PERFORMANCE OVERALL SCORE: {avg:.4f}")
    print("=" * 60)
    return avg


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING LANGGRAPH AGENT EVALUATION REPORT")
    print("=" * 60)
    run_evaluation()