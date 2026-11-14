import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("evaluate_matcher", ROOT / "scripts" / "evaluate_matcher.py")
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


def test_seed_corpus_is_negative_only_and_honestly_reports_undefined_positive_metrics():
    corpus = json.loads((ROOT / "data" / "adjudications.json").read_text(encoding="utf-8"))
    result = e.evaluate(corpus)

    assert result["case_count"] == 2
    assert result["label_counts"] == {"equivalent": 0, "not_equivalent": 2}
    assert result["confusion_matrix"] == {"tp": 0, "tn": 2, "fp": 0, "fn": 0}
    assert result["metrics"]["accuracy"] == 1.0
    assert result["metrics"]["specificity"] == 1.0
    assert result["metrics"]["precision"] is None
    assert result["metrics"]["recall"] is None
    assert result["metrics"]["f1"] is None
    assert all(row["prediction"] == "withheld" for row in result["cases"])
    assert all(row["correct"] for row in result["cases"])
