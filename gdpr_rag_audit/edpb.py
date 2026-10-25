import re
from pathlib import Path

import pdfplumber

from gdpr_rag_audit.corpus import DATA_DIR, clean, download, write_jsonl

URL = (
    "https://www.edpb.europa.eu/system/files/documents/2023-10/"
    "edpb_guidelines_202007_controllerprocessor_final_fr.pdf"
)
SOURCE = "EDPB 07/2020"
RAW_PATH = DATA_DIR / "edpb_07_2020.pdf"
OUT_PATH = DATA_DIR / "edpb_07_2020.jsonl"

# Pages 1 to 7 hold the cover, version history, summary and table of contents;
# the annex starting on page 57 is a flowchart.
PAGES = range(7, 56)
FOOTER_TOP = 775
# Footnotes are set in 10 pt and their call marks in 6.5 pt, below the 11 pt body.
MIN_BODY_SIZE = 10.5
# Paragraph numbers sit in the left margin.
MARGIN = 60

PARAGRAPH = re.compile(r"^(\d{1,3})\. ")
SECTION = re.compile(r"^(\d+(?:\.\d+)*) (.+)$")
PART = re.compile(r"^PARTIE ([IV]+) [–-] (.+)$")


def is_heading(line: dict) -> bool:
    char = line["chars"][0]
    coloured = char["non_stroking_color"] not in ((0,), None)
    return coloured and (char["size"] >= 12 or "CalibriLight" in char["fontname"])


def body_lines(path: Path):
    with pdfplumber.open(path) as pdf:
        for index in PAGES:
            page = pdf.pages[index]
            page = page.crop((0, 0, page.width, FOOTER_TOP)).filter(
                lambda obj: obj["object_type"] != "char" or obj["size"] >= MIN_BODY_SIZE
            )
            yield from page.extract_text_lines(x_tolerance=1)


def join(lines: list[str]) -> str:
    text = ""
    for line in lines:
        text += line if text.endswith("-") or not text else " " + line
    text = clean(text.replace("", "•"))
    # Removing footnote call marks leaves a space before the punctuation that followed them.
    return re.sub(r" ([.,])", r"\1", text)


def title_case(text: str) -> str:
    return text.capitalize() if text.isupper() else text


def parse(path: Path) -> list[dict]:
    passages = []
    part = None
    sections: dict[int, str] = {}
    heading_lines: list[str] = []
    number = context = None
    lines: list[str] = []

    def flush_paragraph():
        if number:
            passages.append({
                "id": f"EDPB-07-2020-{number}",
                "source": SOURCE,
                "context": context,
                "text": join(lines),
            })

    def apply_heading():
        nonlocal part
        if not heading_lines:
            return
        text = join(heading_lines)
        heading_lines.clear()
        if match := PART.match(text):
            part = f"Partie {match[1]} ({title_case(match[2])})"
            sections.clear()
        elif match := SECTION.match(text):
            depth = match[1].count(".") + 1
            for deeper in [d for d in sections if d >= depth]:
                del sections[deeper]
            sections[depth] = f"{match[1]} ({title_case(match[2])})"
        else:
            sections.clear()
            sections[1] = title_case(text)

    for line in body_lines(path):
        if is_heading(line):
            # A numbered line starts a new heading; any other line continues a wrapped one.
            if PART.match(line["text"]) or SECTION.match(line["text"]):
                apply_heading()
            heading_lines.append(line["text"])
            continue
        apply_heading()
        match = PARAGRAPH.match(line["text"])
        if match and line["x0"] < MARGIN and int(match[1]) == (number or 0) + 1:
            flush_paragraph()
            number = int(match[1])
            levels = [part, *(sections[d] for d in sorted(sections))]
            context = " › ".join([SOURCE, *filter(None, levels), f"§{number}"])
            lines = []
        lines.append(line["text"])
    flush_paragraph()
    return passages


def main() -> None:
    download(URL, RAW_PATH)
    write_jsonl(parse(RAW_PATH), OUT_PATH)


if __name__ == "__main__":
    main()
