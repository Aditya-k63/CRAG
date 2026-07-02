import streamlit as st
import requests

API_URL = "http://localhost:8000"
API_KEY = "rag-secret-2026"  # Must match your local .env key
HEADERS = {"X-API-Key": API_KEY}

# --- Page Config ---
st.set_page_config(
    page_title="RAG Assistant",
    layout="wide"
)

st.title("🧙‍♂️ RAG Assistant")
st.caption("Upload any PDF and ask questions about it. Enhanced with LangGraph Corrective RAG (CRAG).")

# --- Session State Init ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "last_uploaded" not in st.session_state:
    st.session_state.last_uploaded = None

# --- Sidebar ---
with st.sidebar:
    st.header("📁 Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    # Auto-upload as soon as a new file is selected
    if uploaded_file is not None and uploaded_file.name != st.session_state.last_uploaded:
        with st.spinner(f"Auto-uploading '{uploaded_file.name}'..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                response = requests.post(
                    f"{API_URL}/upload",
                    files=files,
                    headers=HEADERS
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.last_uploaded = uploaded_file.name
                    st.session_state.uploaded_files.append({
                        "name": uploaded_file.name,
                        "chunks": data["chunks_inserted"]
                    })
                    st.success(f"'{uploaded_file.name}' uploaded!")
                    st.info(f"{data['chunks_inserted']} chunks added to knowledge base")

                elif response.status_code == 409:
                    st.session_state.last_uploaded = uploaded_file.name
                    st.warning(f"'{uploaded_file.name}' was already in the knowledge base.")

                else:
                    st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")

            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.divider()

    # --- API Status ---
    st.header("🔌 API Status")
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.status_code == 200:
            data = health.json()
            st.success("API is running online")
            st.caption(f"Cache size: {data.get('cache_size', 0)} entries")
        else:
            st.error("API error returned")
    except:
        st.error("API not reachable")

    st.divider()

    # --- Chat History Controls ---
    st.header("📜 Chat History")
    st.caption(f"{len(st.session_state.messages)} messages in this session")

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Built with FastAPI + pgvector + NVIDIA Cloud + LangGraph")

# --- Main: Chat Interface ---

# Display full chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "source_info" in message:
            st.caption(message["source_info"])

# Chat input
if prompt := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get and display assistant answer from the LangGraph agent
    with st.chat_message("assistant"):
        with st.spinner("Agent is reasoning..."):
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": prompt, "top_k": 3},
                    headers=HEADERS
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    
                    # ✏️ Note This Down: Detect if our CRAG Agent used fallback search
                    # If your FastAPI backend returns 'chunks_used' as 1 and the data has web markers, 
                    # we update the ui caption dynamically.
                    chunks_used = data.get("chunks_used", 3)
                    
                    # Check if the text matches a web source indicator or fallback trace
                    if "[Score: 1.000]" in answer or chunks_used == 1:
                        source_caption = "🌐 Source: Self-Corrected Fallback Web Search (DuckDuckGo)"
                    else:
                        source_caption = f"📚 Source: Grounded in {chunks_used} local pgvector database blocks"

                    st.markdown(answer)
                    st.caption(source_caption)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "source_info": source_caption
                    })

                elif response.status_code == 401:
                    st.error("API key invalid. Check your API_KEY configuration settings.")

                else:
                    st.error(f"Failed: {response.json().get('detail', 'Unknown error')}")

            except Exception as e:
                st.error(f"Error executing agent pipeline: {str(e)}")