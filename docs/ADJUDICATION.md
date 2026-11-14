# Adjudication and matcher evaluation

Anticipaid separates **candidate discovery** from **settlement equivalence**.

`data/adjudications.json` is the versioned gold corpus used to evaluate the publication gate. Each case contains the contract text used by the matcher, source URLs, an explicit label, rationale, and confidence.

## Labels

- `equivalent`: the two contracts have been manually reviewed and are sufficiently settlement-equivalent for a price comparison.
- `not_equivalent`: a material difference makes the prices non-comparable as the same proposition.

No `unknown` case belongs in the gold corpus; unresolved candidates remain in the public review queue instead.

## Metrics

`scripts/evaluate_matcher.py` treats `publish_candidate` as the positive prediction. It reports the confusion matrix, accuracy, precision, recall, specificity, and F1.

Metrics whose denominator is absent are emitted as JSON `null`. This is intentional. The seed corpus currently contains only high-confidence negative cases, so precision/recall cannot yet be estimated honestly.

## Adding an adjudication

1. Preserve source URLs and the exact relevant settlement text.
2. State the label and rationale explicitly.
3. Prefer narrow rationale tags over prose-only decisions.
4. Add a regression test when the case exposes a new semantic failure mode.
5. Bump `corpus_version`.
6. Run `python scripts/evaluate_matcher.py` and inspect the case-level prediction before merging.

The corpus is evidence, not training data to be edited until the current matcher looks good.
