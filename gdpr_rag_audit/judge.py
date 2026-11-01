import argparse
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

from groq import Groq

from gdpr_rag_audit.ask import excerpts
from gdpr_rag_audit.evaluate import RESULTS_DIR, state
from gdpr_rag_audit.index import load_passages
from gdpr_rag_audit.questions import load_questions

JUDGE = "qwen/qwen3.8-27b"

FAITHFULNESS = """Tu évalues la fidélité d'une réponse produite par un assistant RGPD à partir d'extraits de textes juridiques.

Une affirmation est un énoncé sur le droit ou sur les faits, réponse directe (« oui », « non ») comprise, lue avec la question.

Une affirmation est appuyée si les extraits fournis, seuls ou ensemble, l'établissent sans connaissance extérieure. Toutes les affirmations de la réponse sont concernées, exemples compris. On juge ce que disent les extraits, pas ce qui est vrai : une affirmation exacte mais absente des extraits n'est pas appuyée, une affirmation qui va plus loin qu'eux non plus. L'emplacement des citations entre crochets n'est pas jugé.

Exemples :
- Appuyée : un extrait dit que le responsable tient un registre des activités de traitement, un autre que ce registre est mis à la disposition de l'autorité sur demande. « Le responsable doit pouvoir présenter son registre à l'autorité qui le demande. »
- Non appuyée, car exacte mais absente des extraits : les extraits portent sur la désignation du délégué à la protection des données, la réponse ajoute que ses coordonnées sont communiquées à l'autorité de contrôle.
- Non appuyée, car plus forte que les extraits : un extrait rend la désignation d'un délégué obligatoire dans certains cas, la réponse dit que tout organisme doit en désigner un.

Réponds uniquement par un objet JSON, avec ces champs dans cet ordre :
- "justification" : ton examen des affirmations de la réponse face aux extraits ;
- "affirmation_en_cause" : une affirmation non appuyée, recopiée telle quelle depuis la réponse (la plus nette s'il y en a plusieurs), ou null ;
- "verdict" : "appuyee" si toutes les affirmations sont appuyées, sinon "affirmation_non_appuyee"."""

ACCURACY = """Tu évalues l'exactitude d'une réponse produite par un assistant RGPD, en la comparant à une réponse de référence.

Une affirmation de fond est une obligation, une condition ou un droit ; un détail ou un exemple n'en est pas une. Seules les affirmations de fond comptent.

{criteria}

Exemples :
{examples}

Réponds uniquement par un objet JSON, avec ces champs dans cet ordre :
- "justification" : ta comparaison des affirmations de fond de la réponse et de la référence ;
{fields}"""

# For each accuracy question: its definition, its example if any, and its output field.
CRITERIA = {
    "contradiction": (
        '- Contradiction : "presente" si une affirmation de fond de la réponse est incompatible avec la référence, "absente" sinon. Une omission n\'est pas une contradiction.',
        "- Contradiction : la référence dispense de représentant un traitement occasionnel, la réponse impose un représentant à tout responsable établi hors de l'Union.",
        '- "contradiction" : "presente" ou "absente"',
    ),
    "couverture": (
        '- Couverture : "complete" si chaque affirmation de fond de la référence se retrouve dans la réponse, quelle que soit la formulation, "incomplete" sinon.',
        None,
        '- "couverture" : "complete" ou "incomplete"',
    ),
    "limite": (
        '- Limite : "signalee" si la réponse dit, même en termes généraux, que les sources ne couvrent pas toute la question, "non_signalee" sinon.',
        "- Limite non signalée : « pour un avis adapté, consultez un juriste », seul, ne dit pas que les sources sont incomplètes.",
        '- "limite" : "signalee" ou "non_signalee"',
    ),
}
QUESTIONS_BY_CATEGORY = {"complete": ["contradiction", "couverture"], "partial": ["contradiction", "limite"]}
LABELS = {
    "verdict": {"appuyee", "affirmation_non_appuyee"},
    "contradiction": {"presente", "absente"},
    "couverture": {"complete", "incomplete"},
    "limite": {"signalee", "non_signalee"},
}


def accuracy_instructions(category: str) -> str:
    criteria = [CRITERIA[name] for name in QUESTIONS_BY_CATEGORY[category]]
    return ACCURACY.format(
        criteria="\n".join(definition for definition, _, _ in criteria),
        examples="\n".join(example for _, example, _ in criteria if example),
        fields=" ;\n".join(field for _, _, field in criteria) + ".",
    )


# A malformed verdict is kept with the raw output, to be reported rather than counted.
def parse(content: str, fields: list[str]) -> dict:
    try:
        data = json.loads(content)
        for field in fields:
            if data.get(field) not in LABELS[field]:
                raise ValueError(f"unexpected {field}: {data.get(field)!r}")
        return data
    except ValueError as error:
        return {"error": str(error), "content": content}


def ask(client: Groq, instructions: str, message: str, fields: list[str]) -> dict:
    response = client.chat.completions.create(
        model=JUDGE,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": instructions}, {"role": "user", "content": message}],
    )
    return parse(response.choices[0].message.content, fields)


def judge(client: Groq, record: dict, question: dict, passages: dict[str, dict]) -> dict:
    provided = [(pid, passages[pid]["context"], passages[pid]["text"]) for pid in record["provided"]]
    message = f"Question : {question['question']}\n\nExtraits fournis :\n\n{excerpts(provided)}\n\nRéponse à évaluer :\n{record['answer']}"
    verdicts = {"id": record["id"], "faithfulness": ask(client, FAITHFULNESS, message, ["verdict"])}
    if record["category"] in QUESTIONS_BY_CATEGORY:
        message = (f"Question : {question['question']}\n\nRéponse de référence :\n{question['reference_answer']}"
                   f"\n\nRéponse à évaluer :\n{record['answer']}")
        verdicts["accuracy"] = ask(client, accuracy_instructions(record["category"]), message, QUESTIONS_BY_CATEGORY[record["category"]])
    return verdicts


def report(runs: list[list[dict]]) -> None:
    for number, run in enumerate(runs, 1):
        counts = Counter()
        errors = []
        for verdicts in run:
            for call in ("faithfulness", "accuracy"):
                result = verdicts.get(call)
                if result is None:
                    continue
                if "error" in result:
                    errors.append(f"{verdicts['id']} {call}")
                    continue
                counts.update(f"{field} {result[field]}" for field in LABELS if field in result)
        print(f"Run {number}: {', '.join(f'{label} {n}' for label, n in sorted(counts.items()))}")
        print(f"  Malformed verdicts: {', '.join(errors) or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("answers", type=Path, help="answers file written by evaluate --answers")
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()

    answers = json.loads(args.answers.read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in load_questions()}
    passages = {p["id"]: p for p in load_passages()}
    records = [r for r in answers["answers"] if state(r["answer"]) == "answer"]
    with Groq(api_key=os.environ["GROQ_API_KEY"]) as client:
        runs = [[judge(client, r, questions[r["id"]], passages) for r in records] for _ in range(args.runs)]

    now = datetime.now()
    config = {"answers": args.answers.name, "date": now.isoformat(timespec="seconds"), "judge": JUDGE, "runs": args.runs}
    path = RESULTS_DIR / f"judge-{args.answers.stem}-{now:%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps({"config": config, "runs": runs}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    report(runs)
    print(f"\nVerdicts written to {path}")


if __name__ == "__main__":
    main()
