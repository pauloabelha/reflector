# Proposal: R2 25-Game Context Spinoff Diagnostic

## Frozen cohort

Use exactly the 25 uniquely named recordings under
`reflector-v164-pivot-goal/reports/v164-public-r1-recordings`, one isolated
runtime per game, in lexicographic game order. The recording trajectory is the
chronological evidence stream. A decision at packet `t` may use only frames and
actions through `t-1`; packet `t`'s action and successor remain held out until
after ranking and branch execution.

`ar25` is a frozen sanity check. No code path recognizes it; the check asserts
the previously measured context hash, parent/child hashes, ranking change, and
level delta if that opportunity occurs naturally.

## Configuration fixed before the run

- Seed: `0`; no stochastic choice is permitted.
- Workers: CLI `--workers`; `0` means `min(25, os.cpu_count())`.
- Context candidates: at most 64 established, depth-0, one-atom, binary,
  all-variable relation schemas, ordered by canonical hash.
- Context polarity: whichever of presence/absence holds in the current
  predecessor.
- Minimum context support: 2 preceding transitions.
- Context criterion: selected-action purity must be strictly greater than the
  unspecialized parent purity.
- Context ordering: descending purity, descending support, canonical hash.
- Parent ambiguity: at least two currently legal opaque actions have preceding
  support.
- Baseline ranking: descending parent support, then opaque action ID.
- Child ranking: descending matching-context support, descending parent
  support, then opaque action ID.
- Live branch budget: at most 64 top-action changes per game. Further changes
  are counted as budget abstentions.
- Actions requiring prospective coordinate/data synthesis are abstentions; no
  coordinate policy is introduced.
- Every counterfactual branch starts from a freshly replayed environment and
  must reproduce the exact predecessor frame hash.

The parent schema is the successful experiment's generic
domain/intervention/codomain schema. A child is the parent DAG plus exactly one
`Before(..., BindingPresent|BindingAbsent, RELATION_HASH)` constraint and one
parent-to-child `spinoff` edge. Repeated identical children are reused.

## Prospective shadow and comparison

For each top-action change, the child predicts the modal
`StructuralDelta(changed|preserved)` among preceding transitions matching both
its context and selected action. The no-spinoff parent predicts the same outcome
from all preceding transitions for its selected action. Predictions are emitted
before either real branch is stepped and resolved afterward against the active
R2 binding-set delta. Counterfactual observations never update the chronological
training runtime.

Treatment versus control is classified in this preregistered order:

1. higher one-step `levels_completed` delta is **improve**; lower is **worsen**;
2. when level deltas tie, treatment-only prospective prediction correctness is
   **improve**, control-only correctness is **worsen**;
3. otherwise the result is **tie**.

The API exposes no per-step score, so `score_delta` is reported as unavailable,
not reconstructed. Completed-level delta is the primary progress measure.

## Metrics and gate

Action-changing precision is `improve / (improve + tie + worsen)` over executed
matched branches. False-spinoff rate is `worsen / executed`. Report transition-
micro and game-macro forward prediction accuracy; inverse accuracy is marked
not applicable because this mechanism has no inverse decoder. Report recurrence
and cross-game reuse by context-schema hash, presence/absence balance,
concentration, abstention reasons, calibration, and every negative case.

Verdict rule:

- `PROMOTE` only if at least 3 independent games contain executed action
  changes, precision is at least 0.60, the completed-level delta is positive,
  and false-spinoff rate is at most 0.15.
- `REJECT` if at least 10 action changes execute and precision is below 0.35 or
  false-spinoff rate exceeds 0.40.
- Otherwise `CONTINUE-DIAGNOSTIC`.

Prediction accuracy alone cannot produce `PROMOTE`.
