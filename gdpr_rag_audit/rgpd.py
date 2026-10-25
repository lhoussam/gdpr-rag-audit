import json
import re
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, Tag

URL = "http://publications.europa.eu/resource/celex/32016R0679"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_PATH = DATA_DIR / "rgpd.html"
OUT_PATH = DATA_DIR / "rgpd.jsonl"

RECITAL_ID = re.compile(r"^rct_\d+$")
ARTICLE_ID = re.compile(r"^art_\d+$")
PARAGRAPH_ID = re.compile(r"^\d{3}\.\d{3}$")
DIVISION_ID = re.compile(r"^cpt_[^.]+(\.sct_\d+)?$")

# Its definitions are self-contained, so each one becomes its own passage.
DEFINITIONS_ARTICLE = "4"


def download() -> None:
    if RAW_PATH.exists():
        return
    DATA_DIR.mkdir(exist_ok=True)
    request = urllib.request.Request(
        URL, headers={"Accept": "application/xhtml+xml", "Accept-Language": "fra"}
    )
    with urllib.request.urlopen(request) as response:
        RAW_PATH.write_bytes(response.read())


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def table_text(table: Tag) -> str:
    rows = table.find("tbody", recursive=False).find_all("tr", recursive=False)
    return "\n".join(
        " ".join(clean(cell.get_text(" ")) for cell in row.find_all("td", recursive=False))
        for row in rows
    )


def content_text(container: Tag) -> str:
    blocks = []
    for child in container.find_all(["p", "table"], recursive=False):
        if child.name == "table":
            blocks.append(table_text(child))
        elif "oj-normal" in child.get("class", []):
            blocks.append(clean(child.get_text(" ")))
    return "\n".join(blocks)


def heading(division: Tag) -> str:
    name = clean(division.find("p", recursive=False).get_text(" "))
    name = name.replace("CHAPITRE", "Chapitre")
    title = clean(division.find("div", class_="eli-title", recursive=False).get_text(" "))
    return f"{name} ({title})"


def parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for note in soup.select(".oj-note-tag"):
        note.decompose()

    passages = []
    for recital in soup.find_all("div", id=RECITAL_ID):
        number = recital["id"].removeprefix("rct_")
        passages.append({
            "id": f"RGPD-cons{number}",
            "source": "RGPD",
            "context": f"RGPD › Considérant {number}",
            "text": content_text(recital),
        })

    for article in soup.find_all("div", id=ARTICLE_ID):
        number = article["id"].removeprefix("art_")
        divisions = reversed(article.find_parents("div", id=DIVISION_ID))
        context = " › ".join(["RGPD", *map(heading, divisions), heading(article)])
        paragraphs = article.find_all("div", id=PARAGRAPH_ID, recursive=False)
        if number == DEFINITIONS_ARTICLE:
            for table in article.find_all("table", recursive=False):
                text = table_text(table)
                index = int(text.split(")")[0])
                passages.append({
                    "id": f"RGPD-art{number}-{index}",
                    "source": "RGPD",
                    "context": f"{context} › {index})",
                    "text": text,
                })
        elif not paragraphs:
            passages.append({
                "id": f"RGPD-art{number}",
                "source": "RGPD",
                "context": context,
                "text": content_text(article),
            })
        for paragraph in paragraphs:
            index = int(paragraph["id"].split(".")[1])
            passages.append({
                "id": f"RGPD-art{number}-{index}",
                "source": "RGPD",
                "context": f"{context} › §{index}",
                "text": content_text(paragraph),
            })
    return passages


def main() -> None:
    download()
    passages = parse(RAW_PATH.read_text(encoding="utf-8"))
    with OUT_PATH.open("w", encoding="utf-8") as out:
        for passage in passages:
            out.write(json.dumps(passage, ensure_ascii=False) + "\n")
    print(f"{len(passages)} passages written to {OUT_PATH}")


if __name__ == "__main__":
    main()
