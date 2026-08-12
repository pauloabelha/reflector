# Checkpoint 002: semantic contract and feedback liveness

Time: 2026-08-12T03:11:34Z

## Predeclared question

Can the generic measurement channel survive real Qwen output, preserve R2's
authority, and revise after rejection without either halting frame zero or
silently retaining a failed semantic candidate?

## Live observations

The first AR25 replay exposed a malformed proposal with three independent
contradictions: a built-in observable carried a custom measurement, the
measurement's spatial roles were reversed, and a binary constraint repeated an
undeclared role. R2 previously accepted that document far enough to retain a
stale goal.

The initial strict compiler repair then exposed a liveness error: rejecting one
goal proposal rejected the valid scratchpad and explanation with it, so the
frame-zero explanation gate halted before any action. Proposal-level
quarantine repaired this without granting the malformed candidate authority.

With direct schema branches, Qwen produced a structurally valid custom
observable. R2 rejected it because no measurable typed tuple satisfied its
required constraint. One information probe induced a seven-member CAE binding;
the opposite probe promoted it from OPEN to SUPPORTED with action-conditioned
vertical translations of -3 and +3.

The next failure was feedback loss. Full CAE cell geometry overflowed the
semantic projection budget, and the emergency projection omitted the rejected
goal and its reason. Compacting CAE to membership/status/transform summaries
preserved the exact rejection record inside the same 12 KB boundary.

Finally, Qwen repeated the failed proposal. Raw-versus-normalized comparison
treated the compiler-added terminal and goal-contract defaults as novelty.
Canonical comparison now recognizes the repetition, retires the failed goal,
preserves the independently valid action alias and scratchpad, and continues
grounded probing. The final observed turn had `goal_proposals: []`; no semantic
control prediction or planner route was fabricated.

## Implementation

- Direct complete `oneOf` branches couple built-in observables to null
  definitions and `proposed_` observables to bounded definitions.
- Dependent compiler checks enforce distinct declared roles, coherent local
  terminals, and compilable measurements.
- Invalid sibling proposals are quarantined instead of invalidating an entire
  semantic response.
- Stable scratchpad prose is permitted; semantic validity does not require
  cosmetic rewriting.
- CAE geometry is compacted before the semantic budget boundary, while causal
  status, membership count, transforms, and rejection feedback are retained.
- Compiler-owned defaults are included in proposal identity. An unchanged
  failed set is retired after new evidence rather than becoming a stale
  attractor.

## Verification

Focused result: 143 passed. Full result: 235 passed and the same pre-existing
missing historical `SUMMARY.json` artifact failure. The live evidence above
came from fresh local Qwen and deterministic-planner Arcade runs, not replayed
outcomes.

## Evidence boundary

This checkpoint establishes contract and feedback liveness, CAE induction, and
correct refusal of an ungroundable semantic measurement. It does **not** show
that Qwen has selected the useful occupancy-to-negative-space relation, that a
semantic proposal has changed control, or that AR25 or another game is solved.
