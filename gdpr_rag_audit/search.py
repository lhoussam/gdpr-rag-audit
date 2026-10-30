import sys

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from gdpr_rag_audit.index import DATABASE_URL, EMBEDDING_MODEL

K = 5


def search(conn: psycopg.Connection, model: SentenceTransformer, question: str, k: int = K) -> list[tuple]:
    embedding = model.encode(question, normalize_embeddings=True)
    return conn.execute(
        "SELECT id, context, text, embedding <=> %s AS distance FROM passages ORDER BY distance LIMIT %s",
        (embedding, k),
    ).fetchall()


def main() -> None:
    question = " ".join(sys.argv[1:])
    model = SentenceTransformer(EMBEDDING_MODEL)
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        for id_, context, text, distance in search(conn, model, question):
            print(f"{1 - distance:.3f}  {id_}\n       {context}\n       {text[:200]}\n")


if __name__ == "__main__":
    main()
