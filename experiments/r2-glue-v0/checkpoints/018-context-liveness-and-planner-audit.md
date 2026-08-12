# Checkpoint 018 — semantic transport liveness and planner audit

## Question

Can the unified semantic-affordance loop preserve its full measurement choice
set over a long live trace, and is its observed improving control actually
coming from the configured multi-step planner?

## Observation before repair

On a fresh AR25 run, Qwen independently proposed `fit` and cited a boundary-gap
measurement. R2 grounded it without a game, palette, shape, or action rule. The
same situated goal improved its best measured residual from 96 through 93, 90,
87, 84, 81, 78, 75, to 69, accumulating nine strict frontier confirmations.
CAE retained a supported composite and learned exact action-conditioned
translations for two commands.

The run then stopped at semantic call 11. Prompt admission measured 14,537
tokens plus a reserved 2,048 output tokens, 201 above Qwen's 16,384-token
window. This was a runtime liveness failure after genuine progress, not a
control plateau or environment terminal.

The planner audit was equally important. Although the controller reported
`PLAN_ELIGIBLE` and the bounded-best-first backend was configured, the published
prospective plan had `mode=fallback`, no predictions, no discrimination pairs,
and no grounded goal contract. The repeated improving command came from
one-step learned causal factorization. No multi-step planning benefit is
claimed.

## Generic repair

Only the Qwen-facing copy of the affordance frontier is compacted. It retains
every opaque opportunity reference, exact measurement template, measurability
and unmeasurability counts, best and runner-up normalized residual,
distinctiveness margin, near-best count, feature support, and scale band. It
removes repeated presentation fields that are exactly derivable from the typed
template, plus duplicated provider metadata and null anti-authority sentinels.

The canonical turn and semantic projection remain unchanged for compiler
validation, response-basis checks, audit, settlement, and Arcade. On the exact
failed frontier, serialized size fell from 10,123 to 8,160 bytes, a 1,963-byte
or 19.4% reduction, with every measurement template preserved. No prompt rule,
game fact, threshold selected from AR25 behavior, or semantic/control authority
was added.

## Verification

- 116 focused semantic-measurement, Qwen-worker, and runtime tests pass.
- The full suite has 277 passes.
- Its only failure is the unchanged historical documentation test whose
  expected `experiments/parallel-cognitive-workspace-v1-16/artifacts/SUMMARY.json`
  is absent.
- A fresh repaired run admitted and completed semantic calls 11 and 12, then
  reached turn 12 with call 13 in progress and no runtime error. The same goal
  reached best residual 68 with nine strict confirmations; CAE remained
  SUPPORTED with support 12. Checkpoint 018 is complete.

## Truthful boundary

The pre-repair trace is strong evidence that the semantic goal, grounded
control, effect learning, settlement, and CAE can cooperate over repeated real
actions. It is not a level completion or score result. The planner remained a
fallback. Checkpoint 019 must make supported mechanisms composable into a
certified prospective route, then test the unchanged architecture across games.
