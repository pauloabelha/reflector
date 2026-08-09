# Compositional macro breadth evaluation v1

This freezes the compositional progress DSL and generic gradient option planner
after their development-only ar25 proof, then reruns the exact 16-game v0 breadth
set with no target-specific changes.  The v0 aggregate result (zero solves) is
known, so this is a post-negative breadth evaluation, not held-out evidence.
No target frame or source was inspected between v0 and this freeze.

For each fresh episode, every legal simple intervention is sampled once from a
reset to learn role-specific translation effects.  The agent enumerates only
the frozen bounded DSL, selects its highest-attention improving macro under a
deterministic ordering, executes at most 64 factual actions, and verifies exact
replay.  All candidates begin at empirical support zero.  The calibration is
causal competence evidence, never goal truth.

No repair, rerun, target substitution, or semantic modification is permitted
after the first episode opens.  Only level-1 completion plus exact replay counts.
