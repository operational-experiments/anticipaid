import importlib.util
import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("evaluate_matcher", ROOT / "scripts" / "evaluate_matcher.py")
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


def test_corpus_classifies_seed_positive_and_negatives():
    corpus = json.loads((ROOT / "data" / "adjudications.json").read_text(encoding="utf-8"))
    result = e.evaluate(corpus)

    assert result["case_count"] == 5
    assert result["label_counts"] == {"equivalent": 1, "not_equivalent": 4}
    assert result["confusion_matrix"] == {"tp": 1, "tn": 4, "fp": 0, "fn": 0}
    assert result["metrics"]["accuracy"] == 1.0
    assert result["metrics"]["specificity"] == 1.0
    assert result["metrics"]["precision"] == 1.0
    assert result["metrics"]["recall"] == 1.0
    assert result["metrics"]["f1"] == 1.0

    rows = {row["case_id"]: row for row in result["cases"]}
    buffalo = rows["nfl-champion-buffalo-2027-2026-11-14"]
    assert buffalo["gold_label"] == "equivalent"
    assert buffalo["prediction"] == "publish_candidate"
    assert buffalo["correct"] is True

def test_corpus_validation_rejects_unknown_label():
    corpus = json.loads((ROOT / "data" / "adjudications.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(corpus)
    broken["cases"][0]["label"] = "maybe"
    with pytest.raises(ValueError, match="invalid label"):
        e.evaluate(broken)


def test_corpus_validation_rejects_duplicate_case_ids():
    corpus = json.loads((ROOT / "data" / "adjudications.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(corpus)
    broken["cases"].append(copy.deepcopy(broken["cases"][0]))
    with pytest.raises(ValueError, match="duplicate case_id"):
        e.evaluate(broken)


def test_adjudication_schema_is_versioned():
    schema = json.loads((ROOT / "data" / "adjudications.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["cases"]["items"]["properties"]["label"]["enum"] == [
        "equivalent", "not_equivalent"
    ]
