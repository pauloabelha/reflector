# Checkpoint 013: semantic goal identity across situated change

Time: 2026-08-12

## Failure

`control_goal_key` included a frame-local defeasible role-candidate ID. When
overlap or occlusion changed visible structural identity, an unchanged semantic
goal lost its progress counters and actor/target trajectories. A low residual
on a new grounding could then masquerade as continuation of the old one.

## Repair

- Semantic goal identity excludes situated candidate identity.
- Candidate groundings remain explicit, distinct, and ranked separately.
- The selected candidate creates persistent role trajectories at settlement.
- Later candidates are checked against those trajectories.
- No game, entity, palette, coordinate, action, or solution is encoded.

## Evidence

- Fresh AR25 reproduced the same probe sequence through the prior reset point.
- After a 27 → 30 probe regression, the semantic goal key remained unchanged.
- Both role trajectory IDs remained unchanged.
- Seven accumulated progress confirmations survived; the next planned action
  produced the eighth.
- The run continued on the same tracked pair rather than switching to a
  misleading residual-7 grounding.
- 148 focused tests pass.
- The full suite has 252 passes and one unchanged missing historical artifact
  failure.

This establishes situated identity continuity. It does not establish an AR25
terminal or score improvement.
