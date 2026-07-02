import os
import pickle
import json
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

def get_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    # ✏️ Note This Down: Core system safeguard to activate extension inside python runtime
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    
    register_vector(conn)
    return conn

def ingest_data():
    # ✏️ Note This Down: Automatically initializes database schema tables 
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_sections (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    meta JSONB,
                    embedding VECTOR(384)
                );
                CREATE INDEX IF NOT EXISTS document_sections_hnsw_idx 
                ON document_sections USING hnsw (embedding vector_cosine_ops);
            """)
        conn.commit()
        conn.close()
        print("✅ Database tables verified/created successfully.")
    except Exception as e:
        print(f"❌ Table Creation Error: {e}")
        return

    # Graceful check for Option A workflow
    try:
        with open("processed_data.pkl", "rb") as f:
            data = pickle.load(f)
        print("Pickle file loaded successfully.")
    except FileNotFoundError:
        print("💡 Info: No static 'processed_data.pkl' found. Proceeding with Option A (Streamlit Upload Workflow).")
        return

    try:
        conn = get_connection()
        cur = conn.cursor()
        print("Connected to PostgreSQL for batch insertion.")

        print(f"Inserting {len(data['chunks'])} chunks...")
        for i in range(len(data['chunks'])):
            content = data['chunks'][i]
            metadata = json.dumps(data['metadata'][i])
            embedding = data['embeddings'][i].tolist()

            cur.execute(
                "INSERT INTO document_sections (content, meta, embedding) VALUES (%s, %s, %s)",
                (content, metadata, embedding)
            )

        conn.commit()
        cur.close()
        conn.close()
        print("Database Hydration Complete!")

    except Exception as e:
        print(f"Database Error: {e}")

def sanity_check():
    query = "What is a Python list comprehension?"
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query).tolist()

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT content, 1 - (embedding <=> %s::vector) AS similarity
            FROM document_sections
            ORDER BY similarity DESC
            LIMIT 3;
        """, (query_embedding,))

        rows = cur.fetchall()
        print("\n=== 🔍 SANITY CHECK RESULTS ===")
        if not rows:
            print("Table is currently empty. Ready to receive documents from Streamlit frontend UI! 🚀")
        for row in rows:
            print(f"Score: {row[1]:.4f} | Content: {row[0][:100]}...")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Sanity Check Error: {e}")

if __name__ == "__main__":
    ingest_data()
    sanity_check()