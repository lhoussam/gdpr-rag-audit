import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import psycopg
from mistralai.client import Mistral
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from gdpr_rag_audit.ask import LLM, RETRIES, UNKNOWN, answer, citations, hypothetical_answer, normalize_citations, search_text
from gdpr_rag_audit.index import DATABASE_URL, EMBEDDING_MODEL
from gdpr_rag_audit.questions import EVALUATION_DIR, load_subset
from gdpr_rag_audit.search import K, search

RESULTS_DIR = EVALUATION_DIR.parent / "results"
RETRIEVAL_CATEGORIES = {"complete", "partial"}
EXPECTED = {"complete": "answer", "partial": "answer", "out_of_corpus": "refusal"}


def check_ids(conn: psycopg.Connection, questions: list[dict]) -> int:
    indexed = {id_ for (id_,) in conn.execute("SELECT id FROM passages")}
    missing = sorted({p for q in questions for p in q["passages"]} - indexed)
    if missing:
        sys.exit(f"annotated passages missing from the index: {', '.join(missing)}")
    return len(indexed)


# Rank of each annotated passage in the full ordering of the index, starting at 1.
def ranks(ordering: list[tuple], question: dict) -> list[int]:
    position = {id_: rank for rank, (id_, *_) in enumerate(ordering, 1)}
    return sorted(position[p] for p in question["passages"])


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def retrieval_scores(results: dict[str, list[int]], k: int) -> dict:
    recall = {qid: sum(r <= k for r in found) / len(found) for qid, found in results.items()}
    return {
        "recall": mean(list(recall.values())),
        "ceiling": mean([min(k, len(found)) / len(found) for found in results.values()]),
        "hit": mean([r > 0 for r in recall.values()]),
        "no_passage_found": [qid for qid, r in recall.items() if r == 0],
    }


def report(results: dict[str, list[int]], k: int) -> None:
    for qid, found in results.items():
        print(f"{qid:8} {len(found):2} passages, ranks {' '.join(map(str, found))}")
    scores = retrieval_scores(results, k)
    print(f"\nk = {k}: recall {scores['recall']:.2f} (ceiling {scores['ceiling']:.2f}), hit {scores['hit']:.2f}")
    print(f"No passage found: {', '.join(scores['no_passage_found']) or 'none'}")


# One hypothetical answer per question serves both the retrieval measure and the passages given to the generator.
def run(conn: psycopg.Connection, model: SentenceTransformer, client: Mistral, questions: list[dict], size: int,
        answers: bool) -> tuple[dict[str, list[int]], list[dict]]:
    results, records = {}, []
    for q in questions:
        hypothetical = hypothetical_answer(client, q["question"])
        ordering = search(conn, model, search_text(q["question"], hypothetical), k=size)
        if q["category"] in RETRIEVAL_CATEGORIES:
            results[q["id"]] = ranks(ordering, q)
        if answers:
            provided = [id_ for id_, *_ in ordering[:K]]
            raw = answer(client, q["question"], ordering[:K])
            records.append({
                "id": q["id"],
                "category": q["category"],
                "hypothetical_answer": hypothetical,
                "provided": provided,
                "raw_answer": raw,
                "answer": normalize_citations(raw, set(provided)),
            })
    return results, records


def write_results(name: str, records: list[dict]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    config = {"subset": name, "date": now.isoformat(timespec="seconds"), "llm": LLM, "embedding_model": EMBEDDING_MODEL,
              "retrieval": "question and hypothetical answer", "k": K}
    path = RESULTS_DIR / f"{name}-{now:%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps({"config": config, "answers": records}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


# The instructions ask for the exact refusal sentence; whether an answer signals its limits is left to the judge.
def state(text: str) -> str:
    return "refusal" if text.strip() == UNKNOWN else "answer"


def answer_scores(records: list[dict]) -> dict:
    by_category = {}
    for category, expected in EXPECTED.items():
        group = [r for r in records if r["category"] == category]
        by_category[category] = {
            "states": Counter(state(r["answer"]) for r in group),
            "unexpected": [r["id"] for r in group if state(r["answer"]) != expected],
        }
    answered = [r for r in records if state(r["answer"]) != "refusal"]
    cited = {r["id"]: citations(r["answer"]) for r in answered}
    return {
        "by_category": by_category,
        "answered": len(answered),
        "invalid_citations": [r["id"] for r in answered if cited[r["id"]] - set(r["provided"])],
        "no_valid_citation": [r["id"] for r in answered if not cited[r["id"]] & set(r["provided"])],
    }


def report_answers(records: list[dict]) -> None:
    scores = answer_scores(records)
    print("\nAnswers by category:")
    for category, expected in EXPECTED.items():
        states = scores["by_category"][category]["states"]
        unexpected = scores["by_category"][category]["unexpected"]
        print(f"  {category:13} {states.total():2} questions: {', '.join(f'{s} {n}' for s, n in sorted(states.items()))}"
              f"; not {expected}: {', '.join(unexpected) or 'none'}")
    for label, key in [("Invalid citations", "invalid_citations"), ("No valid citation", "no_valid_citation")]:
        print(f"{label}: {len(scores[key])}/{scores['answered']} answers ({', '.join(scores[key]) or 'none'})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("subset", nargs="?", default="dev")
    parser.add_argument("--answers", action="store_true", help="also generate answers, measure citations and refusals")
    args = parser.parse_args()

    subset = load_subset(args.subset)
    questions = [q for q in subset if q["category"] in RETRIEVAL_CATEGORIES]
    model = SentenceTransformer(EMBEDDING_MODEL)
    with psycopg.connect(DATABASE_URL) as conn, Mistral(api_key=os.environ["MISTRAL_API_KEY"], retry_config=RETRIES) as client:
        register_vector(conn)
        size = check_ids(conn, questions)
        print(f"{args.subset}: {len(questions)} questions, {size} indexed passages\n")
        results, records = run(conn, model, client, subset if args.answers else questions, size, args.answers)
    report(results, K)
    if args.answers:
        path = write_results(args.subset, records)
        report_answers(records)
        print(f"\nAnswers written to {path}")


if __name__ == "__main__":
    main()
