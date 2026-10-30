import json

from gdpr_rag_audit.split import EVALUATION_DIR, GROUPS, load_questions

QUESTIONS = load_questions()
SPLIT = json.loads((EVALUATION_DIR / "split.json").read_text(encoding="utf-8"))


def test_questions_are_well_formed():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids))
    for q in QUESTIONS:
        assert q["origin"] in {"edpb_faq", "commission_qa", "trap"}
        assert q["category"] in {"complete", "partial", "out_of_corpus"}
        assert q["question"] and q["reference_answer"]
        assert bool(q["passages"]) == (q["category"] != "out_of_corpus"), q["id"]
        assert len(q["passages"]) == len(set(q["passages"])), q["id"]


def test_split_covers_each_question_once():
    assigned = SPLIT["dev"] + SPLIT["test"]
    assert sorted(assigned) == sorted(q["id"] for q in QUESTIONS)


def test_groups_stay_on_one_side():
    for group in GROUPS:
        assert set(group) <= set(SPLIT["dev"]) or set(group) <= set(SPLIT["test"]), group
