from gdpr_rag_audit.table import judged, retrieval


def test_retrieval_uses_the_passages_given_to_the_generator():
    questions = [{"id": "Q1", "category": "complete", "passages": ["A", "B"]}, {"id": "Q2", "category": "out_of_corpus", "passages": []}]
    records = [{"id": "Q1", "provided": ["B", "C"]}, {"id": "Q2", "provided": ["C", "D"]}]
    scores = retrieval(questions, records, k=2)
    assert scores["recall"] == 0.5 and scores["ceiling"] == 1 and scores["hit"] == 1


def test_judged_leaves_out_refusals_and_malformed_verdicts():
    records = [
        {"id": "Q1", "category": "complete", "answer": "Oui [A]."},
        {"id": "Q2", "category": "complete", "answer": "Non [A]."},
        {"id": "Q3", "category": "complete", "answer": "Je ne sais pas : les sources disponibles ne couvrent pas cette question."},
    ]
    verdicts = {"Q1": {"faithfulness": {"verdict": "appuyee"}}, "Q2": {"faithfulness": {"error": "…", "content": None}}}
    assert judged(records, verdicts, "faithfulness", "verdict", "appuyee", {"complete"}) == (1, 1, ["Q2"])
