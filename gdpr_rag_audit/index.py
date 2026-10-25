import json

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from gdpr_rag_audit.corpus import DATA_DIR

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
EMBEDDING_MODEL = "BAAI/bge-m3"
SOURCES = ["rgpd.jsonl", "cct_2021_915.jsonl", "edpb_07_2020.jsonl"]


def load_passages() -> list[dict]:
    return [
        json.loads(line)
        for name in SOURCES
        for line in (DATA_DIR / name).open(encoding="utf-8")
    ]


def main() -> None:
    passages = load_passages()
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(
        [f"{p['context']}\n{p['text']}" for p in passages],
        batch_size=8,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        conn.execute("DROP TABLE IF EXISTS passages")
        conn.execute(f"""
            CREATE TABLE passages (
                id text PRIMARY KEY,
                source text NOT NULL,
                context text NOT NULL,
                text text NOT NULL,
                embedding vector({embeddings.shape[1]}) NOT NULL
            )
        """)
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO passages VALUES (%s, %s, %s, %s, %s)",
                [
                    (p["id"], p["source"], p["context"], p["text"], embedding)
                    for p, embedding in zip(passages, embeddings)
                ],
            )
    print(f"{len(passages)} passages indexed")


if __name__ == "__main__":
    main()
