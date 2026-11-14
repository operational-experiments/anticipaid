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
3. Adjudicate genuine positive-equivalence cases before reporting positive precision/recall.
4. Measure candidate persistence and convergence across the history ledger before using temporal behavior as evidence.
5. Determine whether the 10,000-record per-source safety ceilings should be raised, partitioned, or replaced with resumable full-universe scans.
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


---

## E007 — Evaluation and history become first-class evidence

**Purpose.** Prevent matcher changes and scheduled builds from becoming unverifiable one-off outputs.

**Hypothesis.** A small versioned adjudication corpus plus append-only historical snapshots is enough to make matcher quality and time-series behavior measurable without polluting `main` with generated commits.

**Method.**
- create `data/adjudications.json` as a versioned gold corpus;
- evaluate the current publication gate before every live build;
- report undefined metrics as `null` when the corpus lacks the required denominator;
- archive each successful snapshot and evaluation to a separate `history` branch;
- append a stable-ID pair observation ledger for longitudinal analysis;
- block deployment if tests, evaluation, live build, or history persistence fails.

**Initial result.**
- 12 tests passed in the first integrated run.
- Seed corpus: 2 adjudicated `not_equivalent` cases, 0 adjudicated `equivalent` cases.
- Confusion matrix: TN=2, FP=0, TP=0, FN=0.
- Accuracy=1.0 and specificity=1.0.
- Precision, recall, and F1 are undefined because there are no positive gold cases.
- First archived snapshot: `20261114T060831720398Z-ad6744dee6a0`.
- Live snapshot scanned 10,000 Kalshi and 10,000 Polymarket raw records before safety ceilings; 7,727 Polymarket records normalized into usable binary markets.
- 0 comparisons were published; 10 high-scoring candidates were withheld and written to the longitudinal pair ledger.

**Conclusion.** The pipeline now records what it knew, what it refused to claim, how the matcher performed against adjudicated evidence, and what changed over time. The next quality bottleneck is corpus breadth, especially real positive-equivalence adjudications—not a lower lexical threshold.

---

## E008 — First positive control: improve recall without relaxing the threshold

**Purpose.** Add the first adjudicated positive-equivalence case and use it to distinguish an overly conservative matcher from a genuinely incompatible contract pair.

**Corpus expansion.**
- Added two representative below-threshold negatives:
  - Australia PM / Jim Chalmers: materially different 2029 backstop and repeat-election handling.
  - JPMorgan next CEO / Doug Petno: 2028 announcement-based Polymarket trigger versus Kalshi appointment/naming/designation/succession through 2035.
- Added the first positive control:
  - Buffalo to win the 2027 NFL/Pro Football championship. The binary winner proposition is the same; venue settlement timing differs but does not change the ordinary championship outcome.

**Baseline result (v2).**
- Gold labels: 1 equivalent, 4 not-equivalent.
- TP=0, TN=4, FP=0, FN=1.
- Specificity=1.0.
- Recall=0.0.
- Precision undefined because the matcher published no positive candidate.
- The Buffalo positive scored below the 0.76 threshold and was therefore a false negative.

**Diagnosis.**
1. Lexical normalization treated “Pro Football” and “NFL” as unrelated terminology.
2. Temporal comparison used Kalshi's long administrative `close_time` rather than its event-centered `expected_expiration_time`.

Neither defect justified lowering the global lexical threshold.

**Intervention (v3).**
- Add controlled phrase aliases:
  - `National Football League → NFL`
  - `Pro Football → NFL`
  - `NFL league → NFL`
- Preserve Kalshi `expected_expiration_time`.
- Prefer expected resolution time over administrative fallback close time when comparing venue horizons.
- Keep `MATCH_THRESHOLD = 0.76` unchanged.

**Controlled result.**
- TP=1, TN=4, FP=0, FN=0.
- Accuracy=1.0, specificity=1.0, precision=1.0, recall=1.0, F1=1.0 on the current five-case corpus.

**Conclusion.** The first recall improvement came from better representation, not a looser decision boundary. The perfect five-case score is not evidence of generalization; it is evidence that the identified defects were repaired without breaking the existing negative controls. Corpus expansion remains the next requirement before any broader matcher claim.

---

## E009 — Source recall and publication authority are separate failure modes

**Purpose.** Determine whether the missing Buffalo positive was a matcher failure or an ingestion failure, then test whether simply increasing the Kalshi bulk ceiling improves useful coverage.

**Measurement.**
The production build now directly probes every adjudicated contract ID and separately records whether each active gold contract was present in the bulk source scan.

At the 10,000-market Kalshi ceiling:
- 5/5 adjudicated pairs were directly confirmed active on both venues.
- Polymarket bulk contained all five adjudicated markets.
- Kalshi bulk contained four of five.
- Buffalo (`KXSB-27-BUF`) was active but absent from Kalshi bulk.
- active-gold bulk coverage = 0.8.

**20,000-market Kalshi probe.**
- Runtime grew from roughly two minutes to roughly four minutes.
- Kalshi still returned exactly 20,000 records with `truncated=true`.
- Buffalo was still absent.
- active-gold bulk coverage remained 0.8.
- The larger prefix surfaced 39 lexically strong, semantically unblocked candidates.

**Critical failure.**
Manual inspection showed many of those 39 were not equivalent:
- presidential nominee vs vice-presidential nominee;
- election winner vs runoff qualification;
- impeachment vs impeachment-and-removal;
- other superficially similar but materially different propositions.

The automated semantic non-rejection layer therefore did not have enough precision to authorize publication.

**Intervention: v4 publication gate.**
- Keep automated lexical discovery and semantic guards as candidate-generation machinery.
- Quarantine every non-adjudicated pair in the review queue.
- Only a pair labeled `equivalent` in the versioned adjudication corpus may enter the public price-gap table.
- A semantic conflict still overrides adjudication and withholds the pair, making matcher regressions visible.
- Revert the unproductive Kalshi ceiling from 20,000 to 10,000 while a coverage-aware acquisition strategy is developed.

**Result.**
- 21 tests pass.
- Gold matcher evaluation remains TP=1, TN=4, FP=0, FN=0.
- Production source coverage remains 4/5 active adjudicated pairs.
- Public comparable pairs = 0 because the sole approved positive is absent from the current Kalshi bulk prefix.
- Previously exposed false comparisons are no longer publishable.

**Conclusion.**
Matcher quality and source recall must be measured independently. Increasing an arbitrary prefix did not improve gold source recall and increased review noise. More importantly, “no known contradiction” is not strong enough evidence for publication. The next acquisition experiment should operate at the event level and retrieve candidate event markets deliberately rather than increasing a market-count ceiling.

---

## E010 — Event-index enrichment does not beat the prefix baseline

**Purpose.** Test whether a lightweight Kalshi event catalog plus selective nested-event fetch can recover relevant contracts that are missing from the first 10,000 open-market prefix.

**Method.**
- Fetch up to 10,000 open Kalshi events without nested markets.
- Match event title/subtitle against Polymarket questions using discriminative token overlap.
- Require at least two shared discriminative tokens.
- Fetch nested markets only for selected event tickers using the documented `tickers` filter.
- Union those markets with the 10,000-market baseline.
- Measure active adjudication coverage independently.

**Representation correction during test.**
The first selector test failed because `champion` and `championship` were normalized as unrelated. Added a controlled `championship → champion` normalization rather than lowering the two-token requirement.

**Result.**
- 23 tests passed.
- Event catalog returned exactly 10,000 events with `truncated=true`.
- 3,592 event families were selected.
- 25,596 nested markets were fetched.
- 21,509 markets were new beyond the baseline.
- Effective Kalshi universe grew to 31,509 unique markets.
- Buffalo was still absent.
- Active-gold bulk coverage remained 4/5 = 0.8.
- The enrichment therefore increased network work and matcher input substantially without improving measured gold source recall.

**Conclusion.**
The first event-index strategy is too broad and still inherits an arbitrary event-prefix cutoff. It is disabled in scheduled production.

The next acquisition architecture should persist a Kalshi event catalog across runs: bootstrap the catalog separately, then maintain it with the API's `min_updated_ts` change filter. Candidate-event retrieval can operate over that persistent catalog without repeatedly fetching or arbitrarily truncating the event universe.
