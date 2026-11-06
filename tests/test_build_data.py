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


def test_one_sided_number_is_not_automatically_rejected():
    assert b.match_score("Will X happen?", "Will X happen before 2028?") > 0


def test_similar_questions_match():
    a = "Will the Federal Reserve cut interest rates before January 1 2027?"
    c = "Will the Federal Reserve cut interest rates before January 1, 2027?"
    assert b.match_score(a, c) > 0.90


def test_semantic_horizon_conflict():
    k = {
        "match_text": "Will Callum Turner be the next James Bond?",
        "context": "Actor cast as James Bond before 2030",
        "rules_primary": "If Callum Turner is cast before Jan 1, 2030, resolves Yes.",
        "rules_secondary": "",
        "early_close_condition": "",
        "close_time": "2030-01-01T15:00:00Z",
    }
    p = {
        "question": "Callum Turner announced as next James Bond?",
        "description": "Resolves Yes if announced by December 31, 2026.",
        "resolution_source": "",
        "end_time": "2027-01-01T04:59:00Z",
    }
    reasons = b.semantic_conflicts(k, p)
    assert any("horizon years differ" in x for x in reasons)


def test_semantic_interim_conflict():
    k = {
        "match_text": "Will Yair Lapid be the next Prime Minister of Israel?",
        "context": "",
        "rules_primary": "",
        "rules_secondary": "Acting or interim appointments count as holding the position.",
        "early_close_condition": "",
        "close_time": None,
    }
    p = {
        "question": "Will Yair Lapid be the next Prime Minister of Israel?",
        "description": "Any interim or caretaker Prime Minister will not count toward resolution.",
        "resolution_source": "",
        "end_time": None,
    }
    reasons = b.semantic_conflicts(k, p)
    assert "acting/interim/caretaker treatment conflicts" in reasons


def test_pair_has_gap_when_unblocked():
    k = [{
        "id":"K","title":"Will Acme launch before January 1 2027?",
        "match_text":"Will Acme launch before January 1 2027?","context":"",
        "rules_primary":"","rules_secondary":"","early_close_condition":"",
        "probability":0.61,"volume":100,"close_time":"2027-01-01T00:00:00Z",
        "url":"https://kalshi.com/"
    }]
    p = [{
        "id":"P","question":"Will Acme launch before January 1, 2027?",
        "description":"","resolution_source":"",
        "probability":0.44,"volume":100,"end_time":"2027-01-01T00:00:00Z",
        "url":"https://polymarket.com/"
    }]
    pairs, withheld = b.build_pairs(k,p)
    assert len(pairs) == 1
    assert not withheld
    assert abs(pairs[0]["gap"] - 0.17) < 1e-9


def test_conflicted_pair_is_withheld():
    k = [{
        "id":"K","title":"Will Person X be the next Prime Minister?",
        "match_text":"Will Person X be the next Prime Minister?","context":"",
        "rules_primary":"","rules_secondary":"Acting or interim appointments count.",
        "early_close_condition":"","probability":0.61,"volume":100,"close_time":None,
        "url":"https://kalshi.com/"
    }]
    p = [{
        "id":"P","question":"Will Person X be the next Prime Minister?",
        "description":"Interim or caretaker appointments will not count.","resolution_source":"",
        "probability":0.44,"volume":100,"end_time":None,"url":"https://polymarket.com/"
    }]
    pairs, withheld = b.build_pairs(k,p)
    assert not pairs
    assert len(withheld) == 1
