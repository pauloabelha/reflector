# Checkpoint 015: goal evidence is not mechanism evidence

Time: 2026-08-12

## Failure

Measured improvement of a semantic potential was credited only inside the
branch that confirmed an already predicted action mechanism. A novel useful
intervention could therefore reduce the grounded goal residual while receiving
no goal support merely because R2 had not yet learned why that command worked.
This coupled two different empirical questions:

1. did the environment move the grounded goal potential to a new best; and
2. did the observed entity displacement match a previously supported effect?

The coupling blocks induction precisely where a new mechanism should be
learned from a successful intervention.

## Repair

- Potential settlement now compares the observed successor against the best
  potential previously observed for the same semantic goal.
- A strict new best increments goal progress evidence independently of the
  mechanism's `OBSERVED`, `CONFIRMED`, or `REFUTED` status.
- Mechanism confirmation continues to update only explanation/mechanism
  evidence.
- A local improvement that merely returns to an old best does not increment
  goal evidence and does not reset frontier stagnation.
- Settlement telemetry exposes `frontier_before`, `frontier_after`, and
  `frontier_advanced`, so the separation is auditable in Arcade and ledgers.
- No game ID, palette value, coordinate, shape, action ID, or semantic verb is
  special-cased.

## Evidence

- A deterministic unit case with no predicted mechanism records
  `mechanism.status=OBSERVED`, advances the goal frontier, and credits one goal
  progress confirmation.
- A worsening followed by positive recovery to the old best records positive
  local progress but `frontier_advanced=false`; support remains one and
  frontier stagnation reaches two.
- In live AR25 turn 8, action 2 moved the grounded residual from 38 to 35.
  Environment settlement recorded `frontier_before=38`,
  `frontier_after=35`, and `frontier_advanced=true`; goal support reached five
  while the separately learned mechanism was confirmed from the observed
  three-cell actor displacement.
- The same settlement retained a supported seven-member CAE composite with
  eight evidence references. CAE support and semantic goal support therefore
  remain distinct, environment-settled records.
- 143 focused tests pass. The full suite has 254 passes and the one unchanged
  missing historical artifact failure.

## Limit

This repairs induction and evidence accounting; it does not add a new semantic
schema vocabulary. Qwen can currently propose a measurable top-level goal or
compose known schema IDs, but cannot yet project a novel relational/dynamic
abduction into typed entity roles, observables, predictions, and
counterconditions. That generic projection boundary is checkpoint 016.
