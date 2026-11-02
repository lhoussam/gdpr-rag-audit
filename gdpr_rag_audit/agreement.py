import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import fmean

# Judge call, judge field and defect label of each measure.
MEASURES = {
    "faithfulness": ("faithfulness", "verdict", "affirmation_non_appuyee"),
    "contradiction": ("accuracy", "contradiction", "presente"),
    "coverage": ("accuracy", "couverture", "incomplete"),
    "limit": ("accuracy", "limite", "non_signalee"),
}
DOUBT = "douteux"
Z_95 = 1.96


def wilson(p: float, n: int) -> tuple[float, float]:
    centre = (p + Z_95**2 / (2 * n)) / (1 + Z_95**2 / n)
    half = Z_95 * math.sqrt(p * (1 - p) / n + Z_95**2 / (4 * n**2)) / (1 + Z_95**2 / n)
    return centre - half, centre + half


def majority(labels: list[str | None]) -> str | None:
    label, count = Counter(labels).most_common(1)[0]
    return label if count > len(labels) / 2 else None


def measure(human: dict[str, dict], runs: list[dict[str, dict]], name: str) -> dict:
    call, field, defect = MEASURES[name]
    labelled = {id_: j[name] for id_, j in human.items() if name in j}
    kept = {id_: label for id_, label in labelled.items() if label != DOUBT}
    # A malformed verdict has no label, so it counts as a disagreement.
    by_run = [{id_: run[id_].get(call, {}).get(field) for id_ in labelled} for run in runs]
    agreement = [fmean(run[id_] == label for id_, label in kept.items()) for run in by_run]
    defects = [id_ for id_, label in kept.items() if label == defect]
    return {
        "judged": len(kept),
        "doubtful": len(labelled) - len(kept),
        "agreement": agreement,
        "mean": fmean(agreement),
        "interval": wilson(fmean(agreement), len(kept)),
        "majority": fmean(majority([run[id_] for run in by_run]) == label for id_, label in kept.items()),
        "stable": sum(len({run[id_] for run in by_run}) == 1 for id_ in labelled),
        "answers": len(labelled),
        "defects": len(defects),
        "found": [sum(run[id_] == defect for id_ in defects) for run in by_run],
        "human_counts": Counter(kept.values()),
        "judge_counts": [Counter(run[id_] for id_ in kept) for run in by_run],
    }


def load(human_path: Path, judge_path: Path) -> tuple[dict[str, dict], list[dict[str, dict]]]:
    human = json.loads(human_path.read_text(encoding="utf-8"))
    judge = json.loads(judge_path.read_text(encoding="utf-8"))
    if human["run"] != judge["config"]["answers"]:
        sys.exit(f"labels are for {human['run']}, verdicts for {judge['config']['answers']}")
    labels = {j["id"]: j for j in human["judgments"]}
    runs = [{v["id"]: v for v in run} for run in judge["runs"]]
    for number, run in enumerate(runs, 1):
        if run.keys() != labels.keys():
            sys.exit(f"run {number} does not cover the judged answers")
    return labels, runs


def report(name: str, result: dict) -> None:
    low, high = result["interval"]
    print(f"{name}: {result['judged']} answers, {result['doubtful']} doubtful excluded")
    print(f"  agreement by run {' '.join(f'{a:.2f}' for a in result['agreement'])}, "
          f"mean {result['mean']:.2f} [{low:.2f}-{high:.2f}], majority vote {result['majority']:.2f}")
    print(f"  identical verdicts across runs: {result['stable']}/{result['answers']}")
    print(f"  defects found by run: {' '.join(f'{f}/{result['defects']}' for f in result['found'])}")
    print(f"  labels: {dict(result['human_counts'])}, judge by run {[dict(c) for c in result['judge_counts']]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("human", type=Path, help="export of the judgment page")
    parser.add_argument("verdicts", type=Path, help="verdicts file written by judge")
    args = parser.parse_args()

    labels, runs = load(args.human, args.verdicts)
    for name in MEASURES:
        report(name, measure(labels, runs, name))


if __name__ == "__main__":
    main()
