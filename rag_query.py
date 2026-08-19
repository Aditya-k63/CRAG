"""Corrective RAG agent built with LangGraph.

Graph flow:
    START -> retrieve -> evaluate -> (generate | web_fallback -> generate) -> END

- retrieve      : hybrid retrieval (BM25 + pgvector, fused with RRF, cross-encoder rerank)
- evaluate      : Groq grades whether the retrieved chunks actually answer the query
- web_fallback  : if grade is "no", DuckDuckGo results replace the DB context
- generate      : Groq writes the final answer grounded in the chosen context
"""
import os
import re
from typing import Literal, TypedDict

from ddgs import DDGS
from groq import Groq
from langgraph.graph import END, START, StateGraph

from config import GROQ_MODEL
from retrieval import retrieve_chunks

# ===================================================
# 1. STATE DEFINITIONS
# ===================================================
class CRAGState(TypedDict):
    query: str
    retrieved_chunks: list
    evaluation: str  # 'yes' or 'no'
    final_answer: str
    top_k: int  # optional: number of chunks to retrieve


# ===================================================
# 2. LAZY CLIENTS (created on first use, cached)
# ===================================================
_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file (see .env.example)."
            )
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def web_search(query: str) -> str:
    """Return a compact text summary of the top DuckDuckGo results."""
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
    lines = []
    for result in results:
        title = result.get("title", "")
        body = result.get("body", "")
        lines.append(f"- {title}: {body}" if body else f"- {title}")
    return "\n".join(lines) if lines else "No online information found."


def _extract_text(message) -> str:
    """Pull usable text out of a chat message regardless of model quirks.

    Some models return the answer in `content`, others in `reasoning`, and
    some wrap it in `<think>` blocks. This normalizes all of those cases.
    """
    content = (message.content or "").strip()
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if cleaned:
        return cleaned
    reasoning = getattr(message, "reasoning", None) or ""
    return reasoning.strip()


# ===================================================
# 3. GRAPH NODES
# ===================================================
def retrieval_node(state: CRAGState) -> dict:
    top_k = state.get("top_k", 3)
    print(f"\n[NODE: RETRIEVER] Hybrid search (BM25 + pgvector + rerank), top_k={top_k}...")
    chunks = retrieve_chunks(state["query"], top_k=top_k)
    print(f"[NODE: RETRIEVER] Retrieved {len(chunks)} chunks.")
    return {"retrieved_chunks": chunks}


def evaluation_node(state: CRAGState) -> dict:
    print("[NODE: EVALUATOR] Inspecting database chunk quality via Groq...")
    chunks = state["retrieved_chunks"]

    if not chunks:
        print("[NODE: EVALUATOR] No chunks found. Rerouting directly.")
        return {"evaluation": "no"}

    context_text = "\n\n".join(f"Content: {content}" for content, _score in chunks)

    try:
        chat_completion = get_groq_client().chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful data analyst checker. Your job is to look at the retrieved "
                        "document context and decide if it contains relevant information (like scores, "
                        "grades, names, or performance metrics) that can help answer the user's question, "
                        "even if it is formatted as a noisy text table or list. Respond with a single word "
                        "string, either 'yes' or 'no'. Do not include any extra text."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User Query: {state['query']}\n"
                        f"Context: {context_text}\n"
                        "Answer exactly 'yes' or 'no':"
                    ),
                },
            ],
            model=GROQ_MODEL,
            temperature=0.0,
            max_tokens=20,
        )
        raw_response = _extract_text(chat_completion.choices[0].message).lower()
        score = "yes" if "yes" in raw_response else "no"
    except Exception as e:
        print(f"[NODE: EVALUATOR] Safeguard handled error: {e}. Defaulting to fallback.")
        score = "no"

    print(f"[NODE: EVALUATOR] Quality assessment grade: '{score.upper()}'")
    return {"evaluation": score}


def web_fallback_node(state: CRAGState) -> dict:
    print("\n[NODE: WEB FALLBACK] Local database content rejected! Launching DuckDuckGo...")
    try:
        web_raw_results = web_search(state["query"])
        formatted_web_chunk = [(web_raw_results, 1.0)]
    except Exception as e:
        print(f"[NODE: WEB FALLBACK] Search error: {e}. Using empty context.")
        formatted_web_chunk = [("No online information found.", 0.0)]
    return {"retrieved_chunks": formatted_web_chunk}


def generator_node(state: CRAGState) -> dict:
    print("\n[NODE: GENERATOR] Creating final answer via Groq...")
    chunks = state["retrieved_chunks"]
    context = "\n\n".join(f"{content}" for content, _score in chunks)

    prompt = f"""You are a helpful assistant. Answer the question using ONLY the background context provided below.
If you are using web search fallback data, summarize it accurately to answer the query.

CRITICAL STYLE INSTRUCTION:
Do not mention formatting tags, formatting wrappers, XML tags, or database blocks in your response. Speak naturally and provide the answer directly without referencing how the data was provided to you.

Context:
{context}

Question: {state["query"]}
Answer:"""

    try:
        chat_completion = get_groq_client().chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.3,
            max_tokens=1024,
        )
        final_text = _extract_text(chat_completion.choices[0].message)
        if not final_text:
            final_text = "The model did not return a response."
    except Exception as e:
        final_text = f"Error generating final response: {e}"

    return {"final_answer": final_text}


# ===================================================
# 4. CONDITIONAL ROUTING EDGE
# ===================================================
def crag_routing_decision(state: CRAGState) -> Literal["generate", "web_fallback"]:
    if state["evaluation"] == "yes":
        print("[ROUTER] Documents approved. Sending straight to generation stage...")
        return "generate"
    print("[ROUTER] Documents rejected as noisy or irrelevant! Rerouting to web tool...")
    return "web_fallback"


# ===================================================
# 5. ASSEMBLE THE COMPILED STATE GRAPH
# ===================================================
workflow = StateGraph(CRAGState)

workflow.add_node("retrieve", retrieval_node)
workflow.add_node("evaluate", evaluation_node)
workflow.add_node("web_fallback", web_fallback_node)
workflow.add_node("generate", generator_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "evaluate")
workflow.add_conditional_edges(
    "evaluate",
    crag_routing_decision,
    {"generate": "generate", "web_fallback": "web_fallback"},
)
workflow.add_edge("web_fallback", "generate")
workflow.add_edge("generate", END)

crag_agent = workflow.compile()


def rag_query(query: str, top_k: int = 3) -> str:
    initial_state: CRAGState = {
        "query": query,
        "retrieved_chunks": [],
        "evaluation": "",
        "final_answer": "",
        "top_k": top_k,
    }
    result = crag_agent.invoke(initial_state)
    return result["final_answer"]
