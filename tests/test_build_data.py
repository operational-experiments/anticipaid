import importlib.util
from pathlib import Path
import json

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
    assert b.match_score("Will Acme launch?", "Will Acme launch before 2028?") > 0


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
    assert any("deadline years differ" in x for x in reasons)


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
    pairs, withheld = b.build_pairs(k, p, {("K", "P")})
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
    pairs, withheld = b.build_pairs(k, p, {("K", "P")})
    assert not pairs
    assert len(withheld) == 1


def test_real_semantic_conflict_fixtures():
    path = Path(__file__).parent / "fixtures" / "real_semantic_conflicts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for case in data["cases"]:
        reasons = b.semantic_conflicts(case["kalshi"], case["polymarket"])
        for fragment in case["expected_reason_fragments"]:
            assert any(fragment in reason for reason in reasons), (case["id"], fragment, reasons)


def test_nfl_alias_normalization_clears_lexical_threshold():
    score = b.match_score(
        "Will Buffalo win the 2027 Pro Football Championship?",
        "Will the Buffalo Bills win the 2027 NFL league championship?",
        "2027-02-14T23:30:00Z",
        "2027-04-01T03:59:00Z",
    )
    assert score >= b.MATCH_THRESHOLD


def test_expected_expiration_prevents_admin_close_time_false_conflict():
    k = {
        "match_text": "Will Buffalo win the 2027 Pro Football Championship?",
        "context": "2027 NFL Champion",
        "rules_primary": "If Buffalo wins the 2027 Pro Football Championship, then the market resolves to Yes.",
        "rules_secondary": "",
        "early_close_condition": "This market will close and expire after a title holder is declared.",
        "close_time": "2029-02-13T23:30:00Z",
        "expected_expiration_time": "2027-02-14T23:30:00Z",
    }
    p = {
        "question": "Will the Buffalo Bills win the 2027 NFL league championship?",
        "description": "This market resolves according to the team that wins the 2027 NFL league championship.",
        "resolution_source": "NFL",
        "end_time": "2027-04-01T03:59:00Z",
    }
    assert b.kalshi_comparison_deadline(k) == "2027-02-14T23:30:00Z"
    assert b.semantic_conflicts(k, p) == []


def test_adjudication_coverage_measures_only_active_gold_pairs(tmp_path, monkeypatch):
    corpus = {
        "corpus_version": "test",
        "cases": [
            {
                "case_id": "covered",
                "label": "equivalent",
                "kalshi": {"id": "K1"},
                "polymarket": {"id": "P1"},
            },
            {
                "case_id": "missing-kalshi",
                "label": "equivalent",
                "kalshi": {"id": "K2"},
                "polymarket": {"id": "P2"},
            },
            {
                "case_id": "inactive",
                "label": "not_equivalent",
                "kalshi": {"id": "K3"},
                "polymarket": {"id": "P3"},
            },
        ],
    }
    path = tmp_path / "adjudications.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")

    kalshi_probe = {
        "K1": {"ok": True, "active": True, "status": "active"},
        "K2": {"ok": True, "active": True, "status": "active"},
        "K3": {"ok": True, "active": False, "status": "closed"},
    }
    poly_probe = {
        "P1": {"ok": True, "active": True, "closed": False},
        "P2": {"ok": True, "active": True, "closed": False},
        "P3": {"ok": True, "active": True, "closed": False},
    }
    monkeypatch.setattr(b, "_probe_kalshi_market", lambda market_id: kalshi_probe[market_id])
    monkeypatch.setattr(b, "_probe_poly_market", lambda market_id: poly_probe[market_id])

    result = b.audit_adjudication_coverage(
        path,
        [{"ticker": "K1"}, {"ticker": "K3"}],
        [{"id": "P1"}, {"id": "P2"}, {"id": "P3"}],
    )

    assert result["eligible_active_pairs"] == 2
    assert result["eligible_both_in_bulk"] == 1
    assert result["eligible_bulk_coverage"] == 0.5

    rows = {row["case_id"]: row for row in result["cases"]}
    assert rows["covered"]["both_in_bulk"] is True
    assert rows["missing-kalshi"]["kalshi_in_bulk"] is False
    assert rows["missing-kalshi"]["polymarket_in_bulk"] is True
    assert rows["inactive"]["eligible_active_pair"] is False


def test_adjudication_coverage_is_null_when_no_gold_pair_is_active(tmp_path, monkeypatch):
    corpus = {
        "corpus_version": "test",
        "cases": [{
            "case_id": "inactive",
            "label": "not_equivalent",
            "kalshi": {"id": "K1"},
            "polymarket": {"id": "P1"},
        }],
    }
    path = tmp_path / "adjudications.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")

    monkeypatch.setattr(
        b, "_probe_kalshi_market",
        lambda market_id: {"ok": True, "active": False, "status": "closed"},
    )
    monkeypatch.setattr(
        b, "_probe_poly_market",
        lambda market_id: {"ok": True, "active": True, "closed": False},
    )

    result = b.audit_adjudication_coverage(path, [], [])
    assert result["eligible_active_pairs"] == 0
    assert result["eligible_both_in_bulk"] == 0
    assert result["eligible_bulk_coverage"] is None


def test_unadjudicated_candidate_is_quarantined():
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
    pairs, withheld = b.build_pairs(k, p)
    assert pairs == []
    assert len(withheld) == 1
    assert withheld[0]["adjudicated"] is False
    assert "not yet adjudicated equivalent" in withheld[0]["reasons"]


def test_load_adjudicated_equivalent_pairs_only_accepts_positive_gold(tmp_path):
    corpus = {
        "cases": [
            {"label":"equivalent","kalshi":{"id":"K1"},"polymarket":{"id":"P1"}},
            {"label":"not_equivalent","kalshi":{"id":"K2"},"polymarket":{"id":"P2"}},
        ]
    }
    path = tmp_path / "adjudications.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")
    assert b.load_adjudicated_equivalent_pairs(path) == {("K1", "P1")}


def test_event_index_selects_nfl_family_from_polymarket_question():
    events = [
        {"event_ticker": "KXSB-27", "title": "2027 NFL Champion", "sub_title": ""},
        {"event_ticker": "KXRAIN", "title": "Rainfall in Phoenix", "sub_title": ""},
    ]
    poly = [
        {"id": "P1", "question": "Will the Buffalo Bills win the 2027 NFL league championship?"},
        {"id": "P2", "question": "Will rainfall in Seattle exceed 2 inches?"},
    ]
    selected = b.select_candidate_event_tickers(events, poly)
    assert "KXSB-27" in selected
    assert "KXRAIN" not in selected


def test_event_index_enrichment_unions_without_duplicate_tickers(monkeypatch):
    baseline = [
        {"ticker": "K1", "title": "baseline"},
    ]
    poly = [{"id": "P1", "question": "Will Buffalo win the NFL championship?"}]
    monkeypatch.setattr(
        b, "fetch_kalshi_event_catalog",
        lambda: ([{"event_ticker": "E1", "title": "NFL Championship", "sub_title": "Buffalo"}], False),
    )
    monkeypatch.setattr(
        b, "fetch_kalshi_events_by_tickers",
        lambda tickers: [
            {"ticker": "K1", "title": "updated"},
            {"ticker": "K2", "title": "new"},
        ],
    )
    merged, stats = b.enrich_kalshi_from_event_catalog(baseline, poly)
    by_id = {m["ticker"]: m for m in merged}
    assert set(by_id) == {"K1", "K2"}
    assert by_id["K1"]["title"] == "updated"
    assert stats["event_catalog_count"] == 1
    assert stats["candidate_event_count"] == 1
    assert stats["new_markets_added"] == 1
