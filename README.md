# Anticipaid

**See the future disagree with itself.**

Anticipaid is an experimental prediction-market comparison site. It ingests public market data, identifies conservative candidate matches across venues, and highlights probability divergence without assuming that similar wording implies identical resolution criteria.

## Architecture

- Static site in `site/`
- Public-data build in `scripts/build_data.py`
- GitHub Actions deployment in `.github/workflows/pages.yml`
- Scheduled rebuild every four hours, with no generated-data commits to `main`

Initial adapters:

- Kalshi public REST market endpoint
- Polymarket Gamma API

## Matching semantics

The output is deliberately called **candidate equivalence**. Lexical similarity is useful for discovery but is not proof that two contracts share settlement criteria, deadlines, resolution sources, or edge-case semantics. Explicitly conflicting numeric terms are rejected before scoring; surviving candidates must clear a conservative similarity threshold.

## Local build

```bash
python scripts/build_data.py --output site/data/latest.json
python -m http.server 8000 -d site
```

Then open <http://localhost:8000>.

## Deployment

Enable **Settings → Pages → Source: GitHub Actions** for this repository. The workflow handles subsequent deployment and scheduled refreshes.

Custom domain: `anticipaid.com`

## Non-goals

Anticipaid does not execute trades and is not financial advice.
