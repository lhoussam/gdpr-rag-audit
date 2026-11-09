import os
import re
import sys

import psycopg
from mistralai.client import Mistral
from mistralai.client.utils import BackoffStrategy, RetryConfig
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from gdpr_rag_audit.index import DATABASE_URL, EMBEDDING_MODEL
from gdpr_rag_audit.search import search

# A dated version rather than an alias, so that results stay comparable over time.
LLM = "ministral-14b-2512"
BRACKETS = re.compile(r"\[([^\]]+)\]")
PASSAGE_ID = re.compile(r"\w+-[\w.-]+")
SUB_POINT = re.compile(r"(.+?)-?[a-z]")
UNKNOWN = "Je ne sais pas : les sources disponibles ne couvrent pas cette question."
# The free tier is sometimes out of capacity (429): retry with growing waits, for up to half an hour.
RETRIES = RetryConfig("backoff", BackoffStrategy(initial_interval=1_000, max_interval=60_000, exponent=2, max_elapsed_time=1_800_000),
                      retry_connection_errors=False)

INSTRUCTIONS = f"""Tu es un assistant d'analyse RGPD. Tu réponds en français, uniquement à partir des extraits fournis, sans connaissances extérieures.
Après chaque affirmation, cite l'identifiant de l'extrait qui la justifie entre crochets, un identifiant par crochet, par exemple [RGPD-art28-2].
Si les extraits ne couvrent qu'une partie de la question, réponds sur cette partie et dis ce que les extraits ne couvrent pas.
Si les extraits ne permettent pas du tout de répondre, réponds exactement : « {UNKNOWN} »"""

# Searching with a hypothetical answer (HyDE) brings everyday questions closer to the wording of the legal texts.
HYPOTHETICAL = """Tu prépares une recherche dans des textes européens de protection des données : le RGPD, les clauses contractuelles types entre responsable du traitement et sous-traitant, et des lignes directrices de l'EDPB.
Rédige en français le passage de texte juridique qui répondrait à la question de l'utilisateur, dans le style et avec les termes de ces textes : énonce de façon générale les règles, conditions, obligations et droits applicables.
Ce passage sert seulement à retrouver les extraits pertinents et n'est pas montré à l'utilisateur. Ne cite aucun numéro d'article, de considérant ou de clause.
Écris un seul paragraphe, comme un paragraphe de ces textes, sans introduction ni commentaire."""


# Brackets also hold ellipses and placeholders; only passage ids count, alone or separated by commas.
def citations(text: str) -> set[str]:
    return {part.strip() for group in BRACKETS.findall(text) for part in group.split(",") if PASSAGE_ID.fullmatch(part.strip())}


# The generator sometimes cites a point of a provided passage (RGPD-art5-1a); the citation is brought back to the passage id.
def normalize_citations(text: str, provided: set[str]) -> str:
    def passage(part: str) -> str:
        id_ = part.strip()
        point = SUB_POINT.fullmatch(id_)
        return point.group(1) if id_ not in provided and point and point.group(1) in provided else id_

    def bracket(match: re.Match) -> str:
        parts = match.group(1).split(",")
        fixed = list(dict.fromkeys(passage(p) for p in parts))
        return match.group(0) if fixed == [p.strip() for p in parts] else f"[{', '.join(fixed)}]"

    return BRACKETS.sub(bracket, text)


def excerpts(passages: list[tuple]) -> str:
    return "\n\n".join(f"[{id_}] {context}\n{text}" for id_, context, text, *_ in passages)


def build_prompt(question: str, passages: list[tuple]) -> str:
    return f"Extraits :\n\n{excerpts(passages)}\n\nQuestion : {question}"


def complete(client: Mistral, instructions: str, message: str) -> str:
    response = client.chat.complete(
        model=LLM,
        temperature=0,
        messages=[{"role": "system", "content": instructions}, {"role": "user", "content": message}],
    )
    return response.choices[0].message.content


def hypothetical_answer(client: Mistral, question: str) -> str:
    return complete(client, HYPOTHETICAL, f"Question : {question}").strip()


# The passages are searched with the question followed by the hypothetical answer, so the question itself is never lost.
def search_text(question: str, hypothetical: str) -> str:
    return f"{question}\n{hypothetical}"


def answer(client: Mistral, question: str, passages: list[tuple]) -> str:
    return complete(client, INSTRUCTIONS, build_prompt(question, passages))


def main() -> None:
    question = " ".join(sys.argv[1:])
    model = SentenceTransformer(EMBEDDING_MODEL)
    with Mistral(api_key=os.environ["MISTRAL_API_KEY"], retry_config=RETRIES) as client:
        hypothetical = hypothetical_answer(client, question)
        with psycopg.connect(DATABASE_URL) as conn:
            register_vector(conn)
            passages = search(conn, model, search_text(question, hypothetical))
        contexts = {id_: context for id_, context, _, _ in passages}
        text = normalize_citations(answer(client, question, passages), set(contexts))
    print(text)

    cited = citations(text)
    print("\nSources citées :")
    for id_ in sorted(cited & contexts.keys()):
        print(f"  [{id_}] {contexts[id_]}")
    if invalid := cited - contexts.keys():
        print("Citations invalides (absentes des extraits fournis) :", ", ".join(sorted(invalid)))


if __name__ == "__main__":
    main()
