import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "rag-secret-2026")  # Must match the backend API_KEY
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(page_title="CRAG Assistant", layout="wide")

# --- Session State ---
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
    st.session_state.order = []
if "current_id" not in st.session_state:
    _sid = str(uuid.uuid4())
    st.session_state.sessions[_sid] = {"title": "New Chat", "messages": []}
    st.session_state.order = [_sid]
    st.session_state.current_id = _sid
if "last_uploaded" not in st.session_state:
    st.session_state.last_uploaded = None


def new_chat() -> None:
    sid = str(uuid.uuid4())
    st.session_state.sessions[sid] = {"title": "New Chat", "messages": []}
    st.session_state.order.insert(0, sid)
    st.session_state.current_id = sid


def current_messages() -> list:
    return st.session_state.sessions[st.session_state.current_id]["messages"]


# --- Sidebar: History + Status ---
with st.sidebar:
    st.button("New Chat", on_click=new_chat, use_container_width=True)
    st.divider()
    st.markdown("**Chat History**")
    for sid in st.session_state.order:
        if sid == st.session_state.current_id:
            continue
        title = st.session_state.sessions[sid]["title"]
        if st.button(title, key=f"history_{sid}", use_container_width=True):
            st.session_state.current_id = sid
            st.rerun()
    st.divider()
    st.markdown("**Status**")
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.status_code == 200:
            cache_size = health.json().get("cache_size", 0)
            st.markdown(":green[Online]")
            st.caption(f"Cache: {cache_size} entries")
        else:
            st.markdown(":red[Offline]")
    except Exception:
        st.markdown(":red[Offline]")
    st.caption("FastAPI + pgvector + Groq + LangGraph")

# --- Main: Chat ---
st.markdown("## CRAG Assistant")
st.caption("Ask questions about your documents. Attach a PDF to expand the knowledge base.")

uploaded_file = st.file_uploader("Attach a PDF", type="pdf", label_visibility="collapsed")
if uploaded_file is not None and uploaded_file.name != st.session_state.last_uploaded:
    with st.spinner(f"Uploading '{uploaded_file.name}'..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            response = requests.post(f"{API_URL}/upload", files=files, headers=HEADERS)
            if response.status_code == 200:
                st.session_state.last_uploaded = uploaded_file.name
                st.toast(f"{response.json().get('chunks_inserted', 0)} chunks added to the knowledge base")
            elif response.status_code == 409:
                st.session_state.last_uploaded = uploaded_file.name
                st.toast("Document already in the knowledge base")
            else:
                st.error(response.json().get("detail", "Upload failed"))
        except Exception as e:
            st.error(f"Error uploading document: {str(e)}")

for message in current_messages():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("source"):
            st.caption(message["source"])

if prompt := st.chat_input("Ask a question about your documents..."):
    session = st.session_state.sessions[st.session_state.current_id]
    session["messages"].append({"role": "user", "content": prompt})
    if session["title"] == "New Chat":
        session["title"] = prompt[:40]

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": prompt, "top_k": 3},
                    headers=HEADERS,
                    timeout=90,
                )
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    chunks_used = data.get("chunks_used", 3)
                    if "[Score: 1.000]" in answer or chunks_used == 1:
                        source_caption = "Source: web search (DuckDuckGo) fallback"
                    else:
                        source_caption = f"Source: grounded in {chunks_used} document blocks"
                    st.markdown(answer)
                    st.caption(source_caption)
                    session["messages"].append(
                        {"role": "assistant", "content": answer, "source": source_caption}
                    )
                elif response.status_code == 401:
                    st.error("API key invalid. Check your API_KEY configuration.")
                else:
                    st.error(response.json().get("detail", "Failed to get an answer"))
            except Exception as e:
                st.error(f"Error executing agent pipeline: {str(e)}")
