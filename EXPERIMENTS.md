# Anticipaid experiment log

Anticipaid is operated as a transparent commercial experiment. This log records hypotheses, interventions, observations, failures, and conclusions that materially affect the product or its claims.

## E001 — Can a static cross-market comparator find useful disagreements?

**Purpose.** Test whether public Kalshi and Polymarket data can support a low-cost automated comparison site.

**Hypothesis.** A conservative lexical matcher over public market metadata will find a non-trivial set of plausible cross-venue equivalents.

**Method.**
- Fetch open Kalshi markets.
- Fetch active Polymarket markets.
- Normalize binary Yes/No prices.
- Candidate generation by token overlap.
- Candidate scoring by Jaccard overlap, sequence similarity, and token coverage.
- Initial publication threshold: 0.76.

**Finding.** Initial run saw 2,200 Kalshi markets but only 100 Polymarket markets and produced zero candidates.

**Conclusion.** Result was invalid as a coverage test. Polymarket's list endpoint capped pages at 100 while the client treated a short response relative to its requested 500 rows as end-of-data.

**Intervention.** Paginate in actual 100-row pages. Result: ~2,000 Polymarket markets ingested.

---

## E002 — Zero matches after complete ingestion

**Purpose.** Explain why complete ingestion still produced zero candidates.

**Finding.** The numeric-consistency guard rejected a pair whenever only one side contained a number. Example: a proposition without a year was rejected against the same proposition containing a year.

**Conclusion.** The guard encoded “number present on one side” as contradiction. That is not logically valid.

**Intervention.** Reject numeric inconsistency only when both sides contain numeric terms and those sets conflict.

---

## E003 — Lexical near-matches after numeric fix

**Purpose.** Inspect the top score distribution instead of lowering thresholds blindly.

**Method.** Emit the strongest near-matches regardless of publication threshold.

**Finding.** Top scores were ~0.42 and dominated by false sports correspondences. Kalshi often exposes terse outcome labels whose semantics depend on their parent event.

**Conclusion.** The matcher lacked event context; threshold tuning would merely manufacture false positives.

**Intervention.** Ingest Kalshi events with nested markets and carry parent event title/subtitle into canonical records.

---

## E004 — Event context improves discovery but harms proposition scoring

**Finding.** Event enrichment surfaced genuinely related cross-venue questions, including Israel PM successor and next James Bond markets, but concatenating umbrella event text into the scored string diluted otherwise near-identical propositions.

**Intervention.** Separate:
- display/context text, used for interpretation;
- proposition text, used for lexical matching when the market title is already question-like.

**Result.** 14 candidates cleared the lexical threshold. Strong Israel successor candidates scored ~0.88–0.90; several James Bond candidates scored ~0.76–0.77.

---

## E005 — High lexical similarity is not settlement equivalence

**Purpose.** Audit the strongest apparent matches against actual settlement terms.

### Israel PM successor

Kalshi Yair Lapid contract:
- first new person to hold the office after issuance;
- acting or interim appointments explicitly count;
- expiry backstop in 2045.

Polymarket Yair Lapid contract:
- next PM after the 2026 parliamentary election (or an early election);
- candidate must be formally sworn in;
- interim or caretaker PM explicitly does not count;
- fallback to “Other” if no qualifying PM by the end of 2027.

**Finding.** The questions are lexically near-identical but the contracts disagree on material settlement semantics.

### Next James Bond — Callum Turner

Kalshi:
- resolves Yes if Callum Turner is cast as the next James Bond before 2030.

Polymarket:
- resolves Yes if officially announced as the next James Bond by the end of 2026.

**Finding.** Same candidate and role, materially different horizon.

**Conclusion.** A price-gap table based on lexical matching alone would misrepresent contract differences as market disagreement.

**Intervention.**
- ingest Kalshi primary/secondary rules and early-close condition;
- ingest Polymarket description/resolution metadata;
- introduce deterministic semantic incompatibility guards;
- publish unblocked candidates separately from a transparent withheld-candidate queue;
- passing the guard remains explicitly weaker than proof of settlement equivalence.

---

## Current research obligations

1. Expand deterministic semantic contradiction coverage without creating a brittle pile of venue-specific regexes.
2. Distinguish scheduled trading/end metadata from actual resolution conditions.
3. Preserve source terms and machine-generated reasons as provenance for every accepted or withheld comparison.
4. Measure precision/recall against a manually adjudicated candidate set before relaxing thresholds.
5. Add historical snapshots so disagreement persistence and convergence can be studied rather than only current price gaps.
6. Treat “no comparable candidates” as a valid result, not a reason to lower quality gates.

---

## E006 — Coverage caps are part of the result

**Purpose.** Determine whether the initial 2,200 Kalshi / 2,000 Polymarket scan limits represented the available open-market universes.

**Finding.**
- Kalshi exceeded 10,000 open contracts before exhaustion, so the 2,200 limit materially truncated coverage.
- Polymarket offset pagination failed with HTTP 422 beyond its deep-offset boundary rather than returning an empty page.

**Conclusion.** A scanner that silently stops at configured page limits cannot claim exhaustive coverage.

**Intervention.**
- publish a per-source `truncated` flag;
- display capped-source status publicly;
- use Polymarket's keyset endpoint with `after_cursor` instead of deep offset pagination;
- retain a high Kalshi safety ceiling while explicitly reporting when it is reached.

