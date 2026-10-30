from gdpr_rag_audit.ask import UNKNOWN, citations
from gdpr_rag_audit.evaluate import answer_scores, retrieval_scores, state


def test_retrieval_scores():
    # Q1: 4 annotated passages, 2 of them in the top 3; Q2: its only passage is ranked 20th.
    scores = retrieval_scores({"Q1": [1, 3, 7, 12], "Q2": [20]}, k=3)
    assert scores["recall"] == (2 / 4 + 0) / 2
    assert scores["ceiling"] == (3 / 4 + 1) / 2
    assert scores["hit"] == 0.5
    assert scores["no_passage_found"] == ["Q2"]


def test_refusal_is_the_exact_sentence():
    assert state(f"  {UNKNOWN}\n") == "refusal"
    assert state(f"Le corpus couvre une partie [RGPD-art5-1]. {UNKNOWN}") == "answer"


def test_citations_keep_only_passage_ids():
    text = "Coupé [...] et à compléter [durée], [RGPD-cons42, RGPD-art7-2] puis [CCT-clause9.1][EDPB-07-2020-93]."
    assert citations(text) == {"RGPD-cons42", "RGPD-art7-2", "CCT-clause9.1", "EDPB-07-2020-93"}


def test_answer_scores():
    records = [
        {"id": "C1", "category": "complete", "provided": ["RGPD-art5-1"], "answer": "Oui [RGPD-art5-1]."},
        {"id": "C2", "category": "complete", "provided": ["RGPD-art5-1"], "answer": "Oui [RGPD-art5-1] [RGPD-art5-1a]."},
        {"id": "C3", "category": "complete", "provided": ["RGPD-art5-1"], "answer": UNKNOWN},
        {"id": "P1", "category": "partial", "provided": ["RGPD-art5-1"], "answer": "Oui, sans source."},
        {"id": "O1", "category": "out_of_corpus", "provided": ["RGPD-art5-1"], "answer": UNKNOWN},
        {"id": "O2", "category": "out_of_corpus", "provided": ["RGPD-art5-1"], "answer": "Oui [RGPD-art5-1]."},
    ]
    scores = answer_scores(records)
    assert scores["by_category"]["complete"]["unexpected"] == ["C3"]
    assert scores["by_category"]["partial"]["unexpected"] == []
    assert scores["by_category"]["out_of_corpus"]["unexpected"] == ["O2"]
    assert scores["answered"] == 4
    assert scores["invalid_citations"] == ["C2"]
    assert scores["no_valid_citation"] == ["P1"]
