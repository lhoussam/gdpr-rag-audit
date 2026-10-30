import json
import sys
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent.parent / "evaluation"
SPLIT_PATH = EVALUATION_DIR / "split.json"


def load_questions() -> list[dict]:
    with (EVALUATION_DIR / "questions.jsonl").open(encoding="utf-8") as lines:
        return [json.loads(line) for line in lines]


def load_split() -> dict[str, list[str]]:
    return json.loads(SPLIT_PATH.read_text(encoding="utf-8"))


def load_subset(name: str) -> list[dict]:
    split = load_split()
    if name not in split:
        sys.exit(f"unknown subset {name!r}, expected one of {', '.join(split)}")
    ids = set(split[name])
    return [q for q in load_questions() if q["id"] in ids]
