import json
from types import SimpleNamespace

import httpx
from groq import BadRequestError

from gdpr_rag_audit.judge import FAITHFULNESS, JUDGE, accuracy_instructions, ask, judge, parse


def test_parse_keeps_valid_verdicts():
    content = json.dumps({"justification": "…", "contradiction": "absente", "couverture": "complete"})
    assert parse(content, ["contradiction", "couverture"])["couverture"] == "complete"


def test_parse_reports_malformed_verdicts():
    for content in ["pas du JSON", '{"verdict": "oui"}', '{"justification": "…"}']:
        result = parse(content, ["verdict"])
        assert "error" in result and result["content"] == content


def test_failed_json_generation_is_a_malformed_verdict():
    body = {"error": {"code": "json_validate_failed", "failed_generation": "max completion tokens reached"}}
    error = BadRequestError("400", response=httpx.Response(400, request=httpx.Request("POST", "https://groq")), body=body)

    def create(**kwargs):
        raise error

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    assert "error" in ask(client, JUDGE, FAITHFULNESS, "…", ["verdict"])


def test_accuracy_instructions_follow_the_category():
    complete, partial = accuracy_instructions("complete"), accuracy_instructions("partial")
    assert '"contradiction"' in complete and '"couverture"' in complete and '"limite"' not in complete
    assert '"contradiction"' in partial and '"limite"' in partial and '"couverture"' not in partial


def test_out_of_corpus_answers_are_only_judged_on_faithfulness():
    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"verdict": "appuyee"}'))])
    calls = []
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: calls.append(kw) or reply)))
    record = {"id": "O1", "category": "out_of_corpus", "provided": ["RGPD-art5-1"], "answer": "Oui [RGPD-art5-1]."}
    passages = {"RGPD-art5-1": {"context": "RGPD, article 5", "text": "Les données sont traitées de manière licite."}}
    verdicts = judge(client, JUDGE, record, {"question": "Q ?", "reference_answer": "R."}, passages)
    assert len(calls) == 1 and "accuracy" not in verdicts
    assert "[RGPD-art5-1] RGPD, article 5\nLes données sont traitées" in calls[0]["messages"][1]["content"]
