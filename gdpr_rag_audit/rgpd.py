import re

from bs4 import BeautifulSoup

from gdpr_rag_audit.corpus import DATA_DIR, write_jsonl
from gdpr_rag_audit.eurlex import (
    ARTICLE_ID,
    content_text,
    download_celex,
    heading,
    load,
    recitals,
    table_text,
)

CELEX = "32016R0679"
SOURCE = "RGPD"
RAW_PATH = DATA_DIR / "rgpd.html"
OUT_PATH = DATA_DIR / "rgpd.jsonl"

PARAGRAPH_ID = re.compile(r"^\d{3}\.\d{3}$")
DIVISION_ID = re.compile(r"^cpt_[^.]+(\.sct_\d+)?$")

# Its definitions are self-contained, so each one becomes its own passage.
DEFINITIONS_ARTICLE = "4"


def parse(soup: BeautifulSoup) -> list[dict]:
    passages = recitals(soup, "RGPD", SOURCE)
    for article in soup.find_all("div", id=ARTICLE_ID):
        number = article["id"].removeprefix("art_")
        divisions = reversed(article.find_parents("div", id=DIVISION_ID))
        context = " › ".join([SOURCE, *map(heading, divisions), heading(article)])
        paragraphs = article.find_all("div", id=PARAGRAPH_ID, recursive=False)
        if number == DEFINITIONS_ARTICLE:
            for table in article.find_all("table", recursive=False):
                text = table_text(table)
                index = int(text.split(")")[0])
                passages.append({
                    "id": f"RGPD-art{number}-{index}",
                    "source": SOURCE,
                    "context": f"{context} › {index})",
                    "text": text,
                })
        elif not paragraphs:
            passages.append({
                "id": f"RGPD-art{number}",
                "source": SOURCE,
                "context": context,
                "text": content_text(article),
            })
        for paragraph in paragraphs:
            index = int(paragraph["id"].split(".")[1])
            passages.append({
                "id": f"RGPD-art{number}-{index}",
                "source": SOURCE,
                "context": f"{context} › §{index}",
                "text": content_text(paragraph),
            })
    return passages


def main() -> None:
    download_celex(CELEX, RAW_PATH)
    write_jsonl(parse(load(RAW_PATH)), OUT_PATH)


if __name__ == "__main__":
    main()
