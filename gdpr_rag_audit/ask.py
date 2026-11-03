import os
import re
import sys

import psycopg
from mistralai.client import Mistral
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from gdpr_rag_audit.index import DATABASE_URL, EMBEDDING_MODEL
from gdpr_rag_audit.search import search

# A dated version rather than an alias, so that results stay comparable over time.
LLM = "ministral-14b-2512"
BRACKETS = re.compile(r"\[([^\]]+)\]")
PASSAGE_ID = re.compile(r"\w+-[\w.-]+")
UNKNOWN = "Je ne sais pas : les sources disponibles ne couvrent pas cette question."

INSTRUCTIONS = f"""Tu es un assistant d'analyse RGPD. Tu réponds en français, uniquement à partir des extraits fournis, sans connaissances extérieures.
Après chaque affirmation, cite l'identifiant de l'extrait qui la justifie entre crochets, un identifiant par crochet, par exemple [RGPD-art28-2].
Si les extraits ne couvrent qu'une partie de la question, réponds sur cette partie et dis ce que les extraits ne couvrent pas.
Si les extraits ne permettent pas du tout de répondre, réponds exactement : « {UNKNOWN} »"""


# Brackets also hold ellipses and placeholders; only passage ids count, alone or separated by commas.
def citations(text: str) -> set[str]:
    return {part.strip() for group in BRACKETS.findall(text) for part in group.split(",") if PASSAGE_ID.fullmatch(part.strip())}


def excerpts(passages: list[tuple]) -> str:
    return "\n\n".join(f"[{id_}] {context}\n{text}" for id_, context, text, *_ in passages)


def build_prompt(question: str, passages: list[tuple]) -> str:
    return f"Extraits :\n\n{excerpts(passages)}\n\nQuestion : {question}"


def answer(client: Mistral, question: str, passages: list[tuple]) -> str:
    response = client.chat.complete(
        model=LLM,
        temperature=0,
        messages=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": build_prompt(question, passages)},
        ],
    )
    return response.choices[0].message.content


def main() -> None:
    question = " ".join(sys.argv[1:])
    model = SentenceTransformer(EMBEDDING_MODEL)
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        passages = search(conn, model, question)
    with Mistral(api_key=os.environ["MISTRAL_API_KEY"]) as client:
        text = answer(client, question, passages)
    print(text)

    contexts = {id_: context for id_, context, _, _ in passages}
    cited = citations(text)
    print("\nSources citées :")
    for id_ in sorted(cited & contexts.keys()):
        print(f"  [{id_}] {contexts[id_]}")
    if invalid := cited - contexts.keys():
        print("Citations invalides (absentes des extraits fournis) :", ", ".join(sorted(invalid)))


if __name__ == "__main__":
    main()
