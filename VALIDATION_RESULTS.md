# Validation results

Run date: 2026-07-27.

## Conclusion

The current broad Reflector thesis is **not validated**. The final synthetic
holdout verdict is `mixed`: the same Kaggle-exportable policy passes legality
and determinism checks, beats random and a score-only controller, and solves
the invariant-control, contextual-control, and rare-object-click diagnostics.
It solves none of the temporal-sequence levels, and reflecting abstraction has
zero causal efficiency effect relative to disabling it.

These are synthetic mechanism results, not ARC-AGI-3 scores.

## Untouched confirmation set

The final run used paired seeds 10,000–10,029 (960 total runs):

| Preregistered criterion | Result |
| --- | --- |
| All actions legal | Pass: 100% |
| Full minus random completion | Pass: +0.256, 95% bootstrap CI [0.161, 0.344] |
| Full minus score-only completion | Pass: +0.248, 95% CI [0.142, 0.349] |
| Abstraction efficiency effect | Fail: +0.000, 95% CI [0.000, 0.000] |
| Contextual completion | Pass: 100% |
| Rare-object-click completion | Pass: 100% |
| Temporal-sequence completion | Fail: 0% |

The full agent's mean completed-run efficiencies were 0.884 for invariant
control, 0.570 for contextual control, 1.000 for rare-object click, and 0.000
for temporal sequence. A minimal full-frame context table solved 74.6% of
temporal levels and won 46.7% of those games, demonstrating that the diagnostic
is tractable under the same budgets.

The canonical report is
[`validation-results-holdout.json`](validation-results-holdout.json), SHA-256
`337fa3878ef6d3edad3ad0b12290c635b3ce047180b4c4b8562dca70326758e6`.

## Failure-driven development trail

The first seed-0–29 run found that byte-identical observations after distinct
actions were being discarded. It returned `not_supported`
(`5b62f423f9df35400fec08ca82730b9f5912418d0bf2176ca48e91c10613ad08`).

After transition identity and context-conditioned schema selection were fixed,
the second run isolated a planner defect: global plans overrode negative local
evidence. It remained `not_supported`
(`77d285558d3a4a4314ca54bc509be9bc08add4c921b93fe01f28d434a11e8bf5`).

Gating plan bonuses on direct contextual evidence produced a `mixed`
development result
(`b418e477d697e045a6a6bae080d97c0740cb99e25f7d5b7b05bc2e5992b11a25`).
No code or threshold changed after the seed-10,000 holdout was viewed.

## Interpreted failure

The temporal agent gets trapped by actions that cause visual events without
advancing a level. Its hand-written action utility values movement and frame
change, so repeated sensory change can dominate exploration. More importantly,
the current temporal hypotheses do not compile into a context-sensitive
sequence controller. This is a direct counterexample to the claim that the
present reflection/planning stack already produces useful temporal
abstractions.

The schema mechanism itself has narrower support: after the two correctness
fixes it reliably learns invariant and recurring context-dependent controls.
The rare-color grounding heuristic also works on the mechanism designed to
test it. Neither result establishes ARC generalization.

## Remaining external validation

The official deterministic `bt11` fixture remains a five-level compatibility
test. The required 25-public-game evaluation cannot run anonymously: the
official API returns HTTP 401, and this checkout has no accepted-data
credential or `ARC_API_KEY`. A Kaggle score, public-game completion/RHAE table,
and competition-grade generalization claim therefore remain outstanding.
