import json
import random
from collections import Counter

from gdpr_rag_audit.questions import SPLIT_PATH, load_questions

SEED = 2026
# Questions whose reference answers largely overlap stay on the same side.
GROUPS = [
    ["COM-12", "COM-13", "COM-14"],
    ["COM-07", "COM-09", "COM-10", "COM-11"],
    ["FAQ-03", "FAQ-49"],
    ["FAQ-06", "FAQ-12"],
    ["FAQ-13", "FAQ-31", "FAQ-39"],
    ["FAQ-09", "FAQ-48"],
    ["COM-24", "COM-30"],
    ["COM-32", "COM-35"],
    ["FAQ-05", "FAQ-07"],
    ["FAQ-38", "FAQ-41"],
    ["FAQ-20", "FAQ-28"],
    ["COM-17", "COM-18"],
    ["COM-01", "COM-02"],
]


def features(unit: list[str], strata: dict[str, tuple[str, str]]) -> Counter:
    counts = Counter(total=len(unit))
    for qid in unit:
        category, origin = strata[qid]
        counts.update([category, origin, (category, origin)])
    return counts


def imbalance(dev: Counter, test: Counter) -> int:
    return sum((dev[k] - test[k]) ** 2 for k in dev.keys() | test.keys())


def greedy(units: list[list[str]], strata: dict, rng: random.Random) -> tuple[int, dict[str, list[str]]]:
    sides = {"dev": ([], Counter()), "test": ([], Counter())}
    for unit in units:
        f = features(unit, strata)
        dev, test = sides["dev"][1], sides["test"][1]
        cost = {"dev": imbalance(dev + f, test), "test": imbalance(dev, test + f)}
        side = min(cost, key=lambda s: (cost[s], rng.random()))
        sides[side][0].extend(unit)
        sides[side][1].update(f)
    return imbalance(sides["dev"][1], sides["test"][1]), {name: sorted(ids) for name, (ids, _) in sides.items()}


def split(strata: dict[str, tuple[str, str]]) -> dict[str, list[str]]:
    grouped = {qid for group in GROUPS for qid in group}
    units = GROUPS + [[qid] for qid in sorted(strata) if qid not in grouped]
    # Each odd count leaves at least one question of difference: stop at that minimum.
    minimum = sum(n % 2 for n in features(list(strata), strata).values())
    rng = random.Random(SEED)
    while True:
        rng.shuffle(units)
        cost, result = greedy(sorted(units, key=len, reverse=True), strata, rng)
        if cost == minimum:
            return result


def main() -> None:
    if SPLIT_PATH.exists():
        print(f"{SPLIT_PATH} already exists, the split is frozen")
        return
    strata = {q["id"]: (q["category"], q["origin"]) for q in load_questions()}
    result = split(strata)
    SPLIT_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"{len(result['dev'])} dev and {len(result['test'])} test questions written to {SPLIT_PATH}")


if __name__ == "__main__":
    main()
