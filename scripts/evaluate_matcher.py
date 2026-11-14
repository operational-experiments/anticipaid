#!/usr/bin/env python3
"""Evaluate the current matcher against versioned adjudicated contract pairs."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("anticipaid_build_data", HERE / "build_data.py")
matcher = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(matcher)


def ratio(num, den):
    return None if den == 0 else num / den


ALLOWED_LABELS = {"equivalent", "not_equivalent"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


def validate_corpus(corpus):
    if not isinstance(corpus, dict):
        raise ValueError("corpus must be an object")
    if corpus.get("schema_version") != "1.0":
        raise ValueError("unsupported adjudication schema_version")
    if not corpus.get("corpus_version"):
        raise ValueError("corpus_version is required")
    cases = corpus.get("cases")
    if not isinstance(cases, list):
        raise ValueError("cases must be an array")

    seen = set()
    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"case {i} must be an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"case {i} missing case_id")
        if case_id in seen:
            raise ValueError(f"duplicate case_id: {case_id}")
        seen.add(case_id)

        if case.get("label") not in ALLOWED_LABELS:
            raise ValueError(f"{case_id}: invalid label")
        if case.get("confidence") not in ALLOWED_CONFIDENCE:
            raise ValueError(f"{case_id}: invalid confidence")
        if not isinstance(case.get("source_urls"), list) or len(case["source_urls"]) < 2:
            raise ValueError(f"{case_id}: at least two source_urls required")
        if not isinstance(case.get("rationale_tags"), list) or not case["rationale_tags"]:
            raise ValueError(f"{case_id}: rationale_tags required")
        if not isinstance(case.get("rationale"), str) or not case["rationale"]:
            raise ValueError(f"{case_id}: rationale required")

        k = case.get("kalshi")
        p = case.get("polymarket")
        if not isinstance(k, dict) or not isinstance(p, dict):
            raise ValueError(f"{case_id}: kalshi and polymarket objects required")
        if not k.get("id") or not k.get("match_text"):
            raise ValueError(f"{case_id}: Kalshi id and match_text required")
        if not p.get("id") or not p.get("question"):
            raise ValueError(f"{case_id}: Polymarket id and question required")
    return corpus


def evaluate_case(case):
    k, p = case["kalshi"], case["polymarket"]
    score = matcher.match_score(
        k.get("match_text") or "",
        p.get("question") or "",
        k.get("close_time"),
        p.get("end_time"),
    )
    conflicts = matcher.semantic_conflicts(k, p)
    lexical_candidate = score >= matcher.MATCH_THRESHOLD
    publish_candidate = lexical_candidate and not conflicts
    if publish_candidate:
        prediction = "publish_candidate"
    elif lexical_candidate:
        prediction = "withheld"
    else:
        prediction = "not_candidate"

    return {
        "case_id": case["case_id"],
        "gold_label": case["label"],
        "confidence": case.get("confidence"),
        "match_score": round(score, 6),
        "lexical_candidate": lexical_candidate,
        "semantic_conflicts": conflicts,
        "prediction": prediction,
        "correct": (
            publish_candidate if case["label"] == "equivalent"
            else not publish_candidate
        ),
    }


def evaluate(corpus):
    validate_corpus(corpus)
    rows = [evaluate_case(case) for case in corpus["cases"]]
    tp = sum(r["gold_label"] == "equivalent" and r["prediction"] == "publish_candidate" for r in rows)
    fn = sum(r["gold_label"] == "equivalent" and r["prediction"] != "publish_candidate" for r in rows)
    fp = sum(r["gold_label"] == "not_equivalent" and r["prediction"] == "publish_candidate" for r in rows)
    tn = sum(r["gold_label"] == "not_equivalent" and r["prediction"] != "publish_candidate" for r in rows)
    total = tp + tn + fp + fn

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "matcher_method_version": matcher.METHOD_VERSION,
        "match_threshold": matcher.MATCH_THRESHOLD,
        "corpus_version": corpus["corpus_version"],
        "case_count": total,
        "label_counts": {
            "equivalent": tp + fn,
            "not_equivalent": tn + fp,
        },
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "metrics": {
            "accuracy": ratio(tp + tn, total),
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "specificity": ratio(tn, tn + fp),
            "f1": None if (2 * tp + fp + fn) == 0 else (2 * tp) / (2 * tp + fp + fn),
        },
        "notes": [
            "null metrics mean the corpus does not yet contain the denominator needed to estimate them.",
            "An unblocked candidate is not proof of settlement equivalence; evaluation measures the publication gate against adjudicated labels.",
        ],
        "cases": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/adjudications.json")
    ap.add_argument("--output", default="site/data/evaluation.json")
    args = ap.parse_args()

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    result = evaluate(corpus)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(out),
        "corpus_version": result["corpus_version"],
        "case_count": result["case_count"],
        "metrics": result["metrics"],
    }, indent=2))


if __name__ == "__main__":
    main()
