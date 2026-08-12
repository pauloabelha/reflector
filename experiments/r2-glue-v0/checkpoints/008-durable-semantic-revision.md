# Checkpoint 008: durable semantic revision

Time: 2026-08-12

## Failure

DC22 exposed a split semantic state. Qwen accumulated cited action aliases but
kept copying its frame-0 explanation and “no prior state” note. When R2 reached
the explicit repeated-nonprogress threshold, the goal proposal was retired but
the stale explanation was still accepted. A rejection alone was insufficient
because candidate retirement removed the transient failure signal.

## Repair

New transition evidence plus an explicit unsupported R2 semantic failure starts
a durable revision obligation. It clears only when a valid semantic response
changes `notes` and at least one of `explanation`, `goal`, or `expectation`.
Rejections and candidate retirement do not clear it. Episode and level
boundaries do.

This is a structural epistemic contract. It contains no game identifier,
palette value, geometry, action meaning, verb mapping, or elapsed-turn rule.

## Evidence

- 135 focused planner, CAE, semantic-measure, and runtime tests pass.
- The full suite has 246 passes and the unchanged missing historical artifact
  failure.
- Exact DC22 replay rejected call 4 as stale after two grounded nonprogress
  observations.
- Calls after candidate retirement remained rejected; call 7 reported
  `evidence-stale-semantic-revision-pending`.
- Grounded R2 control continued while stale semantics were denied fresh status.

No level completion or score improvement is claimed.
