import os
from typing import TypedDict, Literal
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Core Groq & LangGraph Utilities
from groq import Groq
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, START, END

load_dotenv()

# ===================================================
# 1. INITIALIZE GROQ CLIENT & EMBEDDER
# ===================================================
embedder = SentenceTransformer('all-MiniLM-L6-v2')
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    register_vector(conn)
    return conn

# ===================================================
# 2. STATE DEFINITIONS
# ===================================================
class CRAGState(TypedDict):
    query: str
    retrieved_chunks: list
    evaluation: str        # 'yes' or 'no'
    final_answer: str

web_search_tool = DuckDuckGoSearchRun()

# ===================================================
# 3. GRAPH NODES (The Action Blocks)
# ===================================================

def retrieval_node(state: CRAGState) -> dict:
    print(f"\n[NODE: RETRIEVER] Querying local PostgreSQL Vector store...")
    query_text = state["query"]
    query_embedding = embedder.encode(query_text).tolist()
    
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT content, 1 - (embedding <=> %s::vector) AS similarity
        FROM document_sections
        ORDER BY similarity DESC
        LIMIT 3;
    """, (query_embedding,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"[NODE: RETRIEVER] Found {len(results)} chunks in pgvector.")
    return {"retrieved_chunks": results}


def evaluation_node(state: CRAGState) -> dict:
    print("[NODE: EVALUATOR] Inspecting database chunk quality via Groq...")
    chunks = state["retrieved_chunks"]
    
    if not chunks:
        print("[NODE: EVALUATOR] No chunks found. Rerouting directly.")
        return {"evaluation": "no"}
    
    context_text = "\n\n".join([f"Content: {content}" for content, score in chunks])
    
    try:
        # ✏️ Note This Down: Groq handles conversational payloads seamlessly without task mapper bugs!
        # ✏️ Note This Down: Softer, layout-aware evaluation prompt to prevent false-negative web routing
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful data analyst checker. Your job is to look at the retrieved document context "
                        "and decide if it contains relevant information (like scores, grades, names, or performance metrics) "
                        "that can help answer the user's question, even if it is formatted as a noisy text table or list. "
                        "Respond with a single word string, either 'yes' or 'no'. Do not include any extra text."
                    )
                },
                {
                    "role": "user",
                    "content": f"User Query: {state['query']}\nContext: {context_text}\nAnswer exactly 'yes' or 'no':"
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=5
        )
        raw_response = chat_completion.choices[0].message.content.strip().lower()
        score = "yes" if "yes" in raw_response else "no"
            
    except Exception as e:
        print(f"[NODE: EVALUATOR] Safeguard handled error: {e}. Defaulting to fallback.")
        score = "no"
    
    print(f"[NODE: EVALUATOR] Quality assessment grade: '{score.upper()}'")
    return {"evaluation": score}


def web_fallback_node(state: CRAGState) -> dict:
    print("\n[NODE: WEB FALLBACK] Local database content rejected! Launching DuckDuckGo...")
    try:
        web_raw_results = web_search_tool.invoke(state["query"])
        formatted_web_chunk = [(web_raw_results, 1.0)]
    except Exception as e:
        print(f"[NODE: WEB FALLBACK] Search error: {e}. Using empty context.")
        formatted_web_chunk = [("No online information found.", 0.0)]
        
    return {"retrieved_chunks": formatted_web_chunk}
def generator_node(state: CRAGState) -> dict:
    print("\n[NODE: GENERATOR] Creating final answer via Groq...")
    chunks = state["retrieved_chunks"]
    context = "\n\n".join([f"{content}" for content, score in chunks])
    
    # ✏️ Note This Down: Explicitly forbid the model from mentioning prompt tags or XML in its output
    prompt = f"""You are a helpful assistant. Answer the question using ONLY the background context provided below.
If you are using web search fallback data, summarize it accurately to answer the query.

CRITICAL STYLE INSTRUCTION:
Do not mention formatting tags, formatting wrappers, XML tags, or database blocks in your response. Speak naturally and provide the answer directly without referencing how the data was provided to you.

Context:
{context}

Question: {state["query"]}
Answer:"""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=512
        )
        final_text = chat_completion.choices[0].message.content.strip()
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
    else:
        print("[ROUTER] Documents rejected as noisy or irrelevant! Rerouting to web tool...")
        return "web_fallback"

# ===================================================
# 5. ASSEMBLING THE COMPLED STATE GRAPH
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
    {
        "generate": "generate",
        "web_fallback": "web_fallback"
    }
)
workflow.add_edge("web_fallback", "generate")
workflow.add_edge("generate", END)

crag_agent = workflow.compile()

def rag_query(query):
    initial_state: CRAGState = {
        "query": query,
        "retrieved_chunks": [],
        "evaluation": "",
        "final_answer": ""
    }
    result = crag_agent.invoke(initial_state)
    return result["final_answer"]