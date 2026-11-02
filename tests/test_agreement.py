from pytest import approx

from gdpr_rag_audit.agreement import majority, measure, wilson


def verdicts(*labels):
    return {f"A{i}": {"id": f"A{i}", "faithfulness": {"verdict": label} if label else {"error": "…"}}
            for i, label in enumerate(labels, 1)}


def test_wilson():
    assert wilson(0.8, 25) == approx((0.609, 0.911), abs=1e-3)


def test_majority_needs_more_than_half():
    assert majority(["appuyee", "appuyee", None]) == "appuyee"
    assert majority(["appuyee", "affirmation_non_appuyee", None]) is None


def test_measure():
    ok, bad = "appuyee", "affirmation_non_appuyee"
    # A4 is doubtful; in run 3 the verdict on A1 is malformed.
    human = {f"A{i}": {"faithfulness": label} for i, label in enumerate([ok, bad, bad, "douteux"], 1)}
    runs = [verdicts(ok, bad, ok, ok), verdicts(ok, bad, bad, ok), verdicts(None, bad, ok, ok)]
    result = measure(human, runs, "faithfulness")
    assert result["judged"] == 3 and result["doubtful"] == 1
    assert result["agreement"] == approx([2 / 3, 1, 1 / 3])
    assert result["majority"] == approx(2 / 3)
    assert result["stable"] == 2
    assert result["defects"] == 2 and result["found"] == [1, 2, 1]
