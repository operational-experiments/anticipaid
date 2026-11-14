import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("archive_snapshot", ROOT / "scripts" / "archive_snapshot.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def test_archive_is_idempotent_and_emits_long_form_observations(tmp_path):
    snapshot = {
        "generated_at": "2026-11-14T06:00:00Z",
        "method_version": "test-v1",
        "stats": {"comparable_candidates": 1, "withheld_candidates": 1},
        "sources": {"kalshi": {"ok": True}, "polymarket": {"ok": True}},
        "pairs": [{
            "match_score": 0.95,
            "gap": 0.12,
            "kalshi": {"id": "K1", "probability": 0.62},
            "polymarket": {"id": "P1", "probability": 0.50},
        }],
        "withheld_candidates": [{
            "match_score": 0.90,
            "gap": 0.02,
            "reasons": ["deadline differs"],
            "kalshi": {"id": "K2", "probability": 0.40},
            "polymarket": {"id": "P2", "probability": 0.42},
        }],
    }
    evaluation = {
        "corpus_version": "test-corpus",
        "case_count": 2,
        "metrics": {"accuracy": 1.0, "precision": None},
    }

    first = a.archive(snapshot, evaluation, tmp_path)
    second = a.archive(snapshot, evaluation, tmp_path)

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert first["snapshot_id"] == second["snapshot_id"]

    ledger = (tmp_path / "ledger.ndjson").read_text(encoding="utf-8").splitlines()
    observations = (tmp_path / "pair-observations.ndjson").read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 1
    assert len(observations) == 2

    rows = [json.loads(line) for line in observations]
    assert {r["pair_key"] for r in rows} == {
        "kalshi:K1|polymarket:P1",
        "kalshi:K2|polymarket:P2",
    }
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "latest-evaluation.json").exists()
