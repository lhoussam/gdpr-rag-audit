import json
import re
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def download(url: str, path: Path, headers: dict[str, str] | None = None) -> None:
    if path.exists():
        return
    DATA_DIR.mkdir(exist_ok=True)
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request) as response:
        path.write_bytes(response.read())


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def write_jsonl(passages: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as out:
        for passage in passages:
            out.write(json.dumps(passage, ensure_ascii=False) + "\n")
    print(f"{len(passages)} passages written to {path}")
