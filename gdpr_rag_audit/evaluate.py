import json
import sys

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from gdpr_rag_audit.index import DATABASE_URL, EMBEDDING_MODEL
from gdpr_rag_audit.search import K, search
from gdpr_rag_audit.split import EVALUATION_DIR, load_questions

RETRIEVAL_CATEGORIES = {"complete", "partial"}


def load_subset(name: str) -> list[dict]:
    split = json.loads((EVALUATION_DIR / "split.json").read_text(encoding="utf-8"))
    if name not in split:
        sys.exit(f"unknown subset {name!r}, expected one of {', '.join(split)}")
    ids = set(split[name])
    return [q for q in load_questions() if q["id"] in ids]


def check_ids(conn: psycopg.Connection, questions: list[dict]) -> int:
    indexed = {id_ for (id_,) in conn.execute("SELECT id FROM passages")}
    missing = sorted({p for q in questions for p in q["passages"]} - indexed)
    if missing:
        sys.exit(f"annotated passages missing from the index: {', '.join(missing)}")
    return len(indexed)


# Rank of each annotated passage in the full ordering of the index, starting at 1.
def ranks(conn: psycopg.Connection, model: SentenceTransformer, question: dict, size: int) -> list[int]:
    position = {id_: rank for rank, (id_, *_) in enumerate(search(conn, model, question["question"], k=size), 1)}
    return sorted(position[p] for p in question["passages"])


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def report(results: dict[str, list[int]], k: int) -> None:
    for qid, found in results.items():
        print(f"{qid:8} {len(found):2} passages, ranks {' '.join(map(str, found))}")
    recall = {qid: sum(r <= k for r in found) / len(found) for qid, found in results.items()}
    ceiling = mean([min(k, len(found)) / len(found) for found in results.values()])
    hit = mean([recall[qid] > 0 for qid in results])
    print(f"\nk = {k}: recall {mean(list(recall.values())):.2f} (ceiling {ceiling:.2f}), hit {hit:.2f}")
    print(f"No passage found: {', '.join(qid for qid, r in recall.items() if r == 0) or 'none'}")


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "dev"
    questions = [q for q in load_subset(name) if q["category"] in RETRIEVAL_CATEGORIES]
    model = SentenceTransformer(EMBEDDING_MODEL)
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        size = check_ids(conn, questions)
        print(f"{name}: {len(questions)} questions, {size} indexed passages\n")
        results = {q["id"]: ranks(conn, model, q, size) for q in questions}
    report(results, K)


if __name__ == "__main__":
    main()
