import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from gdpr_rag_audit.corpus import clean, download

RECITAL_ID = re.compile(r"^rct_\d+$")
ARTICLE_ID = re.compile(r"^art_\d+$")


def download_celex(celex: str, path: Path) -> None:
    download(
        f"http://publications.europa.eu/resource/celex/{celex}",
        path,
        {"Accept": "application/xhtml+xml", "Accept-Language": "fra"},
    )


def load(path: Path) -> BeautifulSoup:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for note in soup.select(".oj-note-tag"):
        note.decompose()
    return soup


def table_text(table: Tag) -> str:
    rows = table.find("tbody", recursive=False).find_all("tr", recursive=False)
    return "\n".join(
        " ".join(clean(cell.get_text(" ")) for cell in row.find_all("td", recursive=False))
        for row in rows
    )


def block_text(block: Tag) -> str | None:
    if block.name == "table":
        return table_text(block)
    if block.name == "p" and "oj-normal" in block.get("class", []):
        return clean(block.get_text(" "))
    return None


def content_text(container: Tag) -> str:
    blocks = (block_text(child) for child in container.find_all(["p", "table"], recursive=False))
    return "\n".join(block for block in blocks if block)


def heading(division: Tag) -> str:
    name = clean(division.find("p", recursive=False).get_text(" "))
    name = name.replace("CHAPITRE", "Chapitre")
    title = division.find("div", class_="eli-title", recursive=False)
    return f"{name} ({clean(title.get_text(' '))})" if title else name


def recitals(soup: BeautifulSoup, prefix: str, source: str) -> list[dict]:
    passages = []
    for recital in soup.find_all("div", id=RECITAL_ID):
        number = recital["id"].removeprefix("rct_")
        passages.append({
            "id": f"{prefix}-cons{number}",
            "source": source,
            "context": f"{source} › Considérant {number}",
            "text": content_text(recital),
        })
    return passages
