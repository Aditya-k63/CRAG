"""Batch ingestion: creates the schema and hydrates the vector store.

Two workflows:
  A) The Streamlit UI uploads PDFs at runtime (no file needed here).
  B) A static `processed_data.pkl` (chunks/metadata/embeddings) is loaded and
     inserted in bulk if present.
"""
import json
import pickle

from config import get_embedder
from db import get_connection, init_db_schema, release_connection


def ingest_data():
    try:
        init_db_schema()
        print("Database tables verified/created successfully.")
    except Exception as e:
        print(f"Table Creation Error: {e}")
        return

    try:
        with open("processed_data.pkl", "rb") as f:
            data = pickle.load(f)
        print("Pickle file loaded successfully.")
    except FileNotFoundError:
        print("Info: No static 'processed_data.pkl' found. Proceeding with the Streamlit Upload Workflow.")
        return

    try:
        conn = get_connection()
        inserted = 0
        try:
            with conn.cursor() as cur:
                for i in range(len(data["chunks"])):
                    content = data["chunks"][i]
                    metadata = json.dumps(data["metadata"][i])
                    embedding = data["embeddings"][i].tolist()
                    cur.execute(
                        "INSERT INTO document_sections (content, meta, embedding) VALUES (%s, %s, %s)",
                        (content, metadata, embedding),
                    )
                    inserted += 1
            conn.commit()
            print(f"Database Hydration Complete! {inserted} chunks inserted.")
        finally:
            release_connection(conn)
    except Exception as e:
        print(f"Database Error: {e}")


def sanity_check():
    query = "What is a Python list comprehension?"
    query_embedding = get_embedder().encode(query).tolist()

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content, 1 - (embedding <=> %s::vector) AS similarity
                    FROM document_sections
                    ORDER BY similarity DESC
                    LIMIT 3;
                    """,
                    (query_embedding,),
                )
                rows = cur.fetchall()

            print("\n=== SANITY CHECK RESULTS ===")
            if not rows:
                print("Table is currently empty. Ready to receive documents from the Streamlit UI.")
            for row in rows:
                print(f"Score: {row[1]:.4f} | Content: {row[0][:100]}...")
        finally:
            release_connection(conn)

    except Exception as e:
        print(f"Sanity Check Error: {e}")


if __name__ == "__main__":
    ingest_data()
    sanity_check()