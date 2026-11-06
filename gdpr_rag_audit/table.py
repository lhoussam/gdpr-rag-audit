import argparse
import json
import sys
from pathlib import Path

from gdpr_rag_audit.agreement import wilson
from gdpr_rag_audit.evaluate import RESULTS_DIR, RETRIEVAL_CATEGORIES, answer_scores, retrieval_scores, state
from gdpr_rag_audit.questions import load_subset


def load(verdicts_path: Path) -> tuple[dict, list[dict], dict[str, dict]]:
    judged = json.loads(verdicts_path.read_text(encoding="utf-8"))
    if len(judged["runs"]) != 1:
        sys.exit(f"{verdicts_path.name}: the table uses a single run of the judge")
    answers = json.loads((RESULTS_DIR / judged["config"]["answers"]).read_text(encoding="utf-8"))
    config = answers["config"] | {"judge": judged["config"]["judge"]}
    return config, answers["answers"], {v["id"]: v for v in judged["runs"][0]}


# The answers file keeps only the k passages given to the generator: further ranks are unknown, but the scores only count ranks up to k.
def retrieval(questions: list[dict], records: list[dict], k: int) -> dict:
    provided = {r["id"]: r["provided"] for r in records}
    ranks = {q["id"]: [provided[q["id"]].index(p) + 1 if p in provided[q["id"]] else k + 1 for p in q["passages"]]
             for q in questions if q["category"] in RETRIEVAL_CATEGORIES}
    return retrieval_scores(ranks, k)


# Judge measures are counted on the answers given; a malformed verdict leaves its answer unjudged.
def judged(records: list[dict], verdicts: dict[str, dict], call: str, field: str, good: str,
           categories: set[str]) -> tuple[int, int, list[str]]:
    results = {r["id"]: verdicts[r["id"]][call] for r in records
               if state(r["answer"]) == "answer" and r["category"] in categories}
    valid = [v for v in results.values() if "error" not in v]
    return sum(v[field] == good for v in valid), len(valid), [id_ for id_, v in results.items() if "error" in v]


def count(x: int, n: int) -> str:
    if n == 0:
        return "0/0"
    low, high = wilson(x / n, n)
    return f"{x}/{n} ({x / n:.0%}, [{low:.0%}-{high:.0%}])"


def column(config: dict, records: list[dict], verdicts: dict[str, dict]) -> tuple[list[tuple[str, str]], list[str]]:
    search = retrieval(load_subset(config["subset"]), records, config["k"])
    answers = answer_scores(records)
    states = {category: s["states"] for category, s in answers["by_category"].items()}
    all_categories = set(states)
    measures = [
        ("Faithful answers (judge)", "faithfulness", "faithfulness", "verdict", "appuyee", all_categories),
        ("No contradiction (judge)", "contradiction", "accuracy", "contradiction", "absente", {"complete", "partial"}),
        ("Complete coverage, complete questions (judge)", "coverage", "accuracy", "couverture", "complete", {"complete"}),
        ("Limits signalled, partial questions (judge)", "limit", "accuracy", "limite", "signalee", {"partial"}),
    ]
    rows = [
        (f"Retrieval: recall@{config['k']} (ceiling)", f"{search['recall']:.2f} ({search['ceiling']:.2f})"),
        (f"Retrieval: hit@{config['k']}", f"{search['hit']:.2f}"),
        ("Answered, complete questions", count(states["complete"]["answer"], states["complete"].total())),
        ("Answered, partial questions", count(states["partial"]["answer"], states["partial"].total())),
        ("Refused, out-of-corpus questions", count(states["out_of_corpus"]["refusal"], states["out_of_corpus"].total())),
        ("Answers with an invalid citation", count(len(answers["invalid_citations"]), answers["answered"])),
        ("Answers without a valid citation", count(len(answers["no_valid_citation"]), answers["answered"])),
    ]
    unjudged = []
    for label, name, call, field, good, categories in measures:
        x, n, errors = judged(records, verdicts, call, field, good, categories)
        rows.append((label, count(x, n)))
        unjudged += [f"{id_} ({name})" for id_ in errors]
    return rows, unjudged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("verdicts", type=Path, nargs="+", help="one verdicts file per column, written by judge")
    args = parser.parse_args()

    loaded = [load(path) for path in args.verdicts]
    columns = [column(*data) for data in loaded]
    print(f"| Measure | {' | '.join(config['subset'] for config, _, _ in loaded)} |")
    print(f"|---|{'---|' * len(loaded)}")
    for i, (label, _) in enumerate(columns[0][0]):
        print(f"| {label} | {' | '.join(rows[i][1] for rows, _ in columns)} |")
    print()
    for (config, _, _), (_, unjudged) in zip(loaded, columns):
        print(f"{config['subset']}: generator {config['llm']}, embeddings {config['embedding_model']}, k = {config['k']}, "
              f"judge {config['judge']}, answers of {config['date'][:10]}; not judged: {', '.join(unjudged) or 'none'}")


if __name__ == "__main__":
    main()
