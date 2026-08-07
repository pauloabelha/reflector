# Phase A: successor-effect attribution

## Status

The trace-only implementation is [effect_attribution.py](../../learning/effect_attribution.py).
It extracts palette-free connected-component forms, normalizes single- and
multi-layer observations, produces bounded predecessor/successor
correspondences, and retains appearance, disappearance, split, and merge
effects. It requires support under two distinct action contexts before
constructing a binding. It has no role labels, action authority, planning, or
game-specific identity.

## Controls

Seven unit controls cover translation attribution, the two-context construction
gate with prospective confirmation, ambiguous same-form correspondence,
layered boundary normalization, non-authoritative split/merge evidence,
falsifier quarantine, and uniform render-gap handling. The complete repository
suite currently passes: **97 tests**.

## Recording replay

The preserved public recordings were used read-only. The adapter treats a
multi-layer level-boundary packet chronologically: its first layer closes the
preceding action and its final layer opens the next action. Thus all 399
recorded action transitions are evaluated.

| recording | transitions | constructed | predictions | confirmations | falsifications |
| --- | ---: | ---: | ---: | ---: | ---: |
| `cn04` | 399 | 6 | 1450 | 1447 | 3 |
| `tu93` | 399 | 7 | 761 | 761 | 0 |
| `ls20` | 399 | 8 | 1559 | 1559 | 0 |

This is diagnostic evidence, not a promotion result. The ledger quarantines
each contradicted binding from future predictions, preserving abstention rather
than false authority. The three `cn04` falsifications are retained as explicit
counterexamples and quarantined; `tu93` and structurally different `ls20` have
clean prospective replays under the frozen criterion. No runtime policy was
changed and no effect binding was promoted to control. The accommodation-policy dataset is
[`accommodation_policy_dataset.json`](accommodation_policy_dataset.json).

## Phase B/C diagnostic

The trace-only role module derives roles only from repeated non-preserved
effect statistics. An episode-local identity refinement using bounded temporal
correspondence and relative relational anchors separates carrier IDs. `cn04`
then yields one controlled candidate with **12/12** prospective confirmations
and zero falsifications. No role received action authority. A unique causal
address was constructed locally from that role, with operator contexts 2 and 5
and a translated-effect preservation contract. Fresh `tu93` and `ls20`
re-grounding abstains, so no concrete binding transfers across games. Results
are recorded in [`role_diagnostic.json`](role_diagnostic.json) and
[`address_diagnostic.json`](address_diagnostic.json).

A frozen majority-statistics role mutation was also rejected: `cn04` produced
51 confirmations and 32 falsifications, while `tu93` and `ls20` produced no
role candidates. It was reverted and is retained only as a falsifier.

## Phase E usefulness diagnostic

The local address reduced `cn04` trace proposals from 1,950 baseline component
proposals to 12 eligible address proposals, with 12/12 confirmations and zero
false activations. Exact-off produced zero eligible proposals. Held-out `tu93`
and `ls20` both abstained exactly like exact-off because fresh re-grounding
constructed no address. This is trace-level proposal constraint, not task
utility: no action policy changed, no novel prediction was produced, and no
`T_break` or progression gain was measured. See
[`usefulness_diagnostic.json`](usefulness_diagnostic.json).

## Next falsifiable move

Freeze this attribution ledger and run the next role-derivation diagnostic only
if the three source falsifiers are either explained by a generic successor
correspondence rule or cause the candidate to abstain. Do not tune thresholds
from the transfer result or grant action authority to the current ledger.
