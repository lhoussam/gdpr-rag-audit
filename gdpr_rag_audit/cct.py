import re

from bs4 import BeautifulSoup

from gdpr_rag_audit.corpus import DATA_DIR, clean, write_jsonl
from gdpr_rag_audit.eurlex import (
    ARTICLE_ID,
    block_text,
    content_text,
    download_celex,
    heading,
    load,
    recitals,
)

CELEX = "32021D0915"
SOURCE = "CCT 2021/915"
RAW_PATH = DATA_DIR / "cct_2021_915.html"
OUT_PATH = DATA_DIR / "cct_2021_915.jsonl"

SECTION = re.compile(r"^SECTION ([IVX]+)$")
CLAUSE = re.compile(r"^Clause (\d+)")
SUBCLAUSE = re.compile(r"^(\d+\.\d+)\.\s+(.+)$")
ANNEX_ID = re.compile(r"^anx_[IVX]+$")


def clauses(soup: BeautifulSoup) -> list[dict]:
    """The clauses are a flat sequence of headings and content: units are rebuilt from the headings."""
    passages = []
    section = clause = unit_id = unit_context = None
    blocks = []
    pending = None

    def flush():
        if blocks:
            passages.append({
                "id": f"CCT-clause{unit_id}",
                "source": SOURCE,
                "context": unit_context,
                "text": "\n".join(blocks),
            })
        blocks.clear()

    for element in soup.find("div", id="anx_1").find_all(["p", "table"], recursive=False):
        if "oj-ti-grseq-1" in element.get("class", []):
            text = clean(element.get_text(" "))
            if match := SECTION.match(text):
                section, pending = f"Section {match[1]}", "section"
            elif match := CLAUSE.match(text):
                flush()
                clause, pending = text, "clause"
                unit_id, unit_context = match[1], f"{SOURCE} › {section} › {clause}"
            elif match := SUBCLAUSE.match(text):
                flush()
                pending = None
                unit_id = match[1]
                unit_context = f"{SOURCE} › {section} › {clause} › {match[1]} ({match[2]})"
            elif pending == "section":
                section, pending = f"{section} ({text.capitalize()})", None
            elif pending == "clause":
                clause, pending = f"{clause} ({text})", None
                unit_context = f"{SOURCE} › {section} › {clause}"
        elif text := block_text(element):
            blocks.append(text)
    flush()
    return passages


def parse(soup: BeautifulSoup) -> list[dict]:
    passages = recitals(soup, "CCT", SOURCE)
    for article in soup.find_all("div", id=ARTICLE_ID):
        number = article["id"].removeprefix("art_")
        passages.append({
            "id": f"CCT-art{number}",
            "source": SOURCE,
            "context": f"{SOURCE} › {heading(article)}",
            "text": content_text(article),
        })
    passages += clauses(soup)
    for annex in soup.find_all("div", id=ANNEX_ID):
        number = annex["id"].removeprefix("anx_")
        title = clean(annex.find_all("p", class_="oj-doc-ti")[1].get_text(" "))
        passages.append({
            "id": f"CCT-annexe{number}",
            "source": SOURCE,
            "context": f"{SOURCE} › Annexe {number} ({title})",
            "text": content_text(annex),
        })
    return passages


def main() -> None:
    download_celex(CELEX, RAW_PATH)
    write_jsonl(parse(load(RAW_PATH)), OUT_PATH)


if __name__ == "__main__":
    main()
