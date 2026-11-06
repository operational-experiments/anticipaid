import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("build_data", Path(__file__).parents[1] / "scripts" / "build_data.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def test_kalshi_probability_midpoint():
    m = {"yes_bid_dollars": "0.40", "yes_ask_dollars": "0.44", "last_price_dollars": "0.41"}
    assert abs(b.kalshi_probability(m) - 0.42) < 1e-9


def test_poly_probability_parses_encoded_arrays():
    m = {"outcomes": '["Yes","No"]', "outcomePrices": '["0.63","0.37"]'}
    assert abs(b.poly_probability(m) - 0.63) < 1e-9


def test_conflicting_numbers_are_rejected():
    assert b.match_score("Will X happen before 2027?", "Will X happen before 2028?") == 0


def test_similar_questions_match():
    a = "Will the Federal Reserve cut interest rates before January 1 2027?"
    c = "Will the Federal Reserve cut interest rates before January 1, 2027?"
    assert b.match_score(a, c) > 0.90


def test_pair_has_gap():
    k = [{"id":"K","title":"Will Acme launch before January 1 2027?","probability":0.61,"volume":100,"close_time":"2027-01-01T00:00:00Z","url":"https://kalshi.com/"}]
    p = [{"id":"P","question":"Will Acme launch before January 1, 2027?","probability":0.44,"volume":100,"end_time":"2027-01-01T00:00:00Z","url":"https://polymarket.com/"}]
    pairs = b.build_pairs(k,p)
    assert len(pairs) == 1
    assert abs(pairs[0]["gap"] - 0.17) < 1e-9
