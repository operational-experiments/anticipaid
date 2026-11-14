#!/usr/bin/env python3
"""Append a generated Anticipaid snapshot to an append-only history tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pair_key(pair):
    k = str((pair.get("kalshi") or {}).get("id") or "")
    p = str((pair.get("polymarket") or {}).get("id") or "")
    return f"kalshi:{k}|polymarket:{p}"


def append_line(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def archive(snapshot, evaluation, root):
    generated = snapshot.get("generated_at")
    if not generated:
        raise ValueError("snapshot missing generated_at")
    stamp = generated.replace("-", "").replace(":", "").replace(".", "").replace("+00:00", "Z")
    date = generated[:10].split("-")
    if len(date) != 3:
        raise ValueError(f"unexpected generated_at: {generated}")
    year, month, day = date

    digest = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()
    snapshot_id = f"{stamp}-{digest[:12]}"

    snapshot_path = root / "snapshots" / year / month / day / f"{snapshot_id}.json"
    if snapshot_path.exists():
        return {"snapshot_id": snapshot_id, "duplicate": True}

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(canonical_bytes(snapshot))

    if evaluation is not None:
        eval_path = root / "evaluations" / year / month / day / f"{snapshot_id}.json"
        eval_path.parent.mkdir(parents=True, exist_ok=True)
        eval_path.write_bytes(canonical_bytes(evaluation))

    ledger = {
        "snapshot_id": snapshot_id,
        "generated_at": generated,
        "sha256": digest,
        "method_version": snapshot.get("method_version"),
        "stats": snapshot.get("stats", {}),
        "sources": snapshot.get("sources", {}),
        "evaluation": None if evaluation is None else {
            "corpus_version": evaluation.get("corpus_version"),
            "case_count": evaluation.get("case_count"),
            "metrics": evaluation.get("metrics"),
        },
    }
    append_line(root / "ledger.ndjson", ledger)

    for compatibility, rows in (
        ("unblocked_candidate", snapshot.get("pairs", [])),
        ("withheld", snapshot.get("withheld_candidates", [])),
    ):
        for pair in rows:
            append_line(root / "pair-observations.ndjson", {
                "snapshot_id": snapshot_id,
                "generated_at": generated,
                "pair_key": pair_key(pair),
                "compatibility": compatibility,
                "match_score": pair.get("match_score"),
                "gap": pair.get("gap"),
                "kalshi_probability": (pair.get("kalshi") or {}).get("probability"),
                "polymarket_probability": (pair.get("polymarket") or {}).get("probability"),
                "reasons": pair.get("reasons", []),
            })

    (root / "latest.json").write_bytes(canonical_bytes(snapshot))
    if evaluation is not None:
        (root / "latest-evaluation.json").write_bytes(canonical_bytes(evaluation))

    return {
        "snapshot_id": snapshot_id,
        "duplicate": False,
        "snapshot_path": str(snapshot_path),
        "pair_observations": len(snapshot.get("pairs", [])) + len(snapshot.get("withheld_candidates", [])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--evaluation")
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    evaluation = None
    if args.evaluation and Path(args.evaluation).exists():
        evaluation = json.loads(Path(args.evaluation).read_text(encoding="utf-8"))

    result = archive(snapshot, evaluation, Path(args.root))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
