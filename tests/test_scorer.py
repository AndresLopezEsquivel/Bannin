"""The stub scorer: a fixed score and the stub's model version."""

from bannin.decision import decide
from bannin.scorer import MODEL_VERSION, Score, StubScorer
from bannin.thresholds import Thresholds


def test_the_stub_returns_its_fixed_score_and_version():
    assert StubScorer().score({}) == Score(value=12.37, model_version="stub-0.1.0")


def test_the_features_dont_change_the_score():
    scorer = StubScorer()
    assert scorer.score({"email_domain": "example.com"}) == scorer.score({})


def test_the_default_score_is_approved_under_the_shipped_thresholds():
    shipped = Thresholds(version="thresholds-v1", review=60, decline=85)
    assert decide(StubScorer().score({}).value, shipped) == "approve"


def test_another_score_keeps_the_model_version():
    assert StubScorer(score=90).score({}) == Score(90, MODEL_VERSION)
