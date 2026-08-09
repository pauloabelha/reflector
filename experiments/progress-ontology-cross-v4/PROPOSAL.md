# Progress Ontology Cross-Game v4

This experiment is frozen before constructing the selected environment.

The selector considers only metadata-tagged `keyboard_click` games, excludes all
previously consumed development targets, and orders candidates by SHA-256 of a
fixed seed plus opaque game ID.  It selects exactly `re86-8af5384d`.

Two fresh arms receive the same initial state and 48-action budget:

1. `r2_cycle`: the unchanged opaque-action cycle baseline.
2. `shared_progress_ontology`: the frozen progress dispatcher, expanded only by
   the pre-selection generic flow-routing mechanism committed in `3f294ec`.

No target frame, source, recording, outcome, or prior target-specific artifact
may be inspected before this freeze.  No code, prompt, threshold, role rule, or
action policy may change after the target is constructed.  PASS requires exact
replay and either a shared-only level-1 completion or at least 25% action saving
when both arms complete.  A typed ontology abstention is reported as ABSTAIN.
