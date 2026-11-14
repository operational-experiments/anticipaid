# Historical snapshot ledger

Scheduled builds archive compact generated results to the repository's `history` branch.

The goal is to measure disagreement persistence, convergence, matcher behavior, and source coverage over time without committing generated data to `main`.

## Layout on `history`

- `data/snapshots/YYYY/MM/DD/<snapshot-id>.json` — complete public snapshot.
- `data/evaluations/YYYY/MM/DD/<snapshot-id>.json` — matcher evaluation for that build.
- `data/ledger.ndjson` — one provenance record per snapshot.
- `data/pair-observations.ndjson` — long-form time series keyed by stable Kalshi/Polymarket IDs.
- `data/latest.json` and `data/latest-evaluation.json` — convenience pointers.

A snapshot ID combines its generation timestamp with a SHA-256 prefix. Re-archiving the same snapshot is idempotent.

## Scope

The history branch stores the compact candidate/review output, not every raw venue market. Source counts and truncation flags are preserved in each ledger entry. If raw-source archival becomes necessary, it should be a separate storage decision with explicit retention/cost semantics.
