# Anticipaid history branch

This branch is the append-only generated evidence ledger for Anticipaid.

Do not develop product code here. Canonical source lives on `main`.

## Generated data

- `data/snapshots/YYYY/MM/DD/<snapshot-id>.json` — complete public snapshots.
- `data/evaluations/YYYY/MM/DD/<snapshot-id>.json` — matcher evaluation paired with each snapshot.
- `data/ledger.ndjson` — one provenance record per archived snapshot.
- `data/pair-observations.ndjson` — longitudinal observations keyed by stable Kalshi/Polymarket IDs.
- `data/latest.json` — most recent public snapshot.
- `data/latest-evaluation.json` — most recent matcher evaluation.

Each scheduled production build archives here before GitHub Pages deployment. A failed archive blocks deployment.

Snapshot IDs combine the generation timestamp with a SHA-256 prefix. Re-archiving an identical snapshot is idempotent.

For implementation and methodology, see the `main` branch.
