# Validation results

Run date: 2026-07-27.

## V3 conclusion

The narrow constructive-accommodation claim is **supported** on its untouched
confirmation split. After identical forced action and scalar-progress
histories, a Kaggle-exportable symbolic descendant constructed an evidenced
condition over proposition-level prediction errors and used it to improve
first-attempt interventions in unseen layouts.

This validates conditional accommodation on one synthetic family. It does not
establish general equilibration, autonomous invention of arbitrary ontologies,
psychological fidelity, or ARC-AGI-3 generalization.

## V3 untouched confirmation set

The run used paired seeds 60,000–60,029 and passed all frozen criteria:

| Preregistered criterion | Result |
| --- | --- |
| All actions legal | Pass: 100% |
| Identical training histories | Pass within every paired seed |
| Isolated constructive completion | Pass: 100% |
| Default full-policy completion | Pass: 100% |
| Constructive minus fixed-ontology efficiency | Pass: +0.0682, 95% bootstrap CI [0.0527, 0.0835] |
| Constructive minus fixed-ontology first-attempt accuracy | Pass: +0.2125, 95% CI [0.1667, 0.2625] |
| Evidenced conditions and target condition constructed | Pass |
| Fixed ontology exposes no operative accommodations | Pass |

The full default agent averaged 18.33 actions against an oracle minimum of 16;
the isolated constructive descendant averaged 19.17 and its fixed-ontology
ablation 20.87. The training action sequence and progress history were
identical across all six policies.

The canonical report is
[`validation-v3-holdout.json`](validation-v3-holdout.json), file SHA-256
`02ec3f7943cf87bbe065148df7770a133fccb2309fe5f7ec3522bf0a7ef7cf50`
and embedded result SHA-256
`4d9a1a164521dbd8670d94c745b8d9969b6e0661b22200f9285cbb3f4787d53b`.
The frozen protocol and development result are recorded in
[`VALIDATION_V3.md`](VALIDATION_V3.md).

## V2 conclusion

The v2 synthetic mechanism claim is **supported** on its untouched confirmation
split. The same Kaggle-exportable policy completes all four diagnostic families
and its learned abstractions and procedures have positive causal efficiency
effects under preregistered ablations.

This is evidence for the mechanisms on known synthetic task families. It is not
an ARC-AGI-3 score, a claim of general intelligence, or evidence of transfer to
an unseen official game.

## V2 untouched confirmation set

The run used paired seeds 30,000–30,029 and passed all nine frozen criteria:

| Preregistered criterion | Result |
| --- | --- |
| All actions legal | Pass: 100% |
| Full minus random completion | Pass: +0.5250, 95% bootstrap CI [0.4616, 0.5941] |
| Full minus score-only completion | Pass: +0.5972, 95% CI [0.5250, 0.6670] |
| Full minus no-abstraction efficiency | Pass: +0.1538, 95% CI [0.1242, 0.1828] |
| Contextual completion | Pass: 100% |
| Rare-object-click completion | Pass: 100% |
| Procedure completion | Pass: 100% |
| Full minus no-planning procedure efficiency | Pass: +0.1874, 95% CI [0.1803, 0.1944] |
| Full minus no-abstraction novel-transfer efficiency | Pass: +0.3429, 95% CI [0.3245, 0.3599] |

The canonical report is
[`validation-v2-holdout.json`](validation-v2-holdout.json), file SHA-256
`420bea3da401d1aa621b6c648fc68441f73d626544e55c94cad15c6dc62c81b0`
and embedded result SHA-256
`c3642664307cd4239569b27d205fb3f7ddc69764de8bb709acf7e31bca5766f2`.
The protocol, including the development-time confound that caused the task
revision before confirmation, is recorded in
[`VALIDATION_V2.md`](VALIDATION_V2.md).

## V1 conclusion

The original broad Reflector thesis was **not validated**. Its final synthetic
holdout verdict is `mixed`: the same Kaggle-exportable policy passes legality
and determinism checks, beats random and a score-only controller, and solves
the invariant-control, contextual-control, and rare-object-click diagnostics.
It solves none of the temporal-sequence levels, and reflecting abstraction has
zero causal efficiency effect relative to disabling it.

These are synthetic mechanism results, not ARC-AGI-3 scores.

## V1 untouched confirmation set

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

## V1 failure-driven development trail

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

## V1 interpreted failure

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
