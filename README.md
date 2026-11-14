# Anticipaid

**See the future disagree with itself.**

Anticipaid is an experimental prediction-market comparison site. It ingests public market data, discovers plausible cross-venue matches, preserves semantic conflicts and source-coverage evidence, and only publishes price gaps for pairs explicitly adjudicated as settlement-equivalent.

## Architecture

- Static site in `site/`
- Live market build in `scripts/build_data.py`
- Versioned adjudication corpus in `data/adjudications.json` with formal schema in `data/adjudications.schema.json`
- Matcher evaluation in `scripts/evaluate_matcher.py`
- Append-only historical snapshot writer in `scripts/archive_snapshot.py`
- GitHub Actions deployment in `.github/workflows/pages.yml`
- Scheduled rebuild every four hours
- Generated snapshots committed to the separate `history` branch, never to `main`

Initial venue adapters:

- Kalshi public REST API
- Polymarket Gamma API with keyset pagination

## Matching semantics

Anticipaid separates three claims that should not be conflated:

1. **Lexical candidate** — two contracts look like they may ask substantially the same thing.
2. **Semantically unblocked candidate** — no implemented deterministic incompatibility rule fires.
3. **Settlement-equivalent pair** — requires adjudicated evidence; automated non-rejection is not proof.

The public comparison table only receives adjudicated equivalent pairs that also pass the current semantic guard. Automated candidates remain in the review queue until adjudication. This is intentionally stricter than the matcher itself.

## Source coverage

Matcher recall and ingestion recall are measured separately. Each production build directly probes the adjudicated venue IDs, determines which gold pairs are currently active, and reports whether those same contracts occurred in the bulk source scan.

Both source scans expose configured ceilings and `truncated` flags. A truncated bulk scan is never represented as exhaustive.

## Evaluation


`data/adjudications.json` is a versioned gold corpus. Current seed cases are high-confidence negatives discovered during real contract audits.

Run:

```bash
python scripts/evaluate_matcher.py --output site/data/evaluation.json
```

Metrics with no valid denominator are emitted as JSON `null`, not zero. Until real positive-equivalence cases are adjudicated, positive precision and recall are intentionally undefined.

See:

- `docs/ADJUDICATION.md`
- `EXPERIMENTS.md`

## Historical data

Every successful scheduled build is archived on the `history` branch before deployment.

The history branch contains:

- immutable timestamped public snapshots
- timestamped matcher evaluations
- `data/ledger.ndjson` provenance records
- `data/pair-observations.ndjson` long-form candidate time series
- latest pointers for convenience

See `docs/HISTORY.md`.

## Local build

```bash
python -m pytest -q tests
python scripts/evaluate_matcher.py --output site/data/evaluation.json
python scripts/build_data.py --output site/data/latest.json
python -m http.server 8000 -d site
```

Then open <http://localhost:8000>.

## Deployment

GitHub Pages deploys from GitHub Actions. The build must pass tests, generate evaluation, fetch the live market snapshot, and archive it to `history` before the Pages artifact is uploaded.

Custom domain: `anticipaid.com`

## Non-goals

Anticipaid does not execute trades and is not financial advice.
