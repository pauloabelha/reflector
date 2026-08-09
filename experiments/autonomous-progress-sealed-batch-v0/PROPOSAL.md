# Autonomous progress synthesis: sealed batch v0

This evaluates one frozen, source-blind goal-synthesis and opaque-control system
on every remaining game in the previously frozen 25-game census after excluding
the nine games used for direct developmental inspection.

The complete target set is fixed before any episode is opened.  No game source,
frame, prior artifact, game identifier, action meaning, or outcome may select a
goal AST or executor.  The same bounded grammar generates competing grounded
progress potentials from the current frame.  Structural regularity changes
attention only; every candidate starts with empirical support zero.  Opaque
actions are calibrated from reset transitions and dispatched only by AST
operator type.

Each target receives at most 64 factual actions, plus at most one reset-based
calibration sample per legal simple action.  A result counts only when level 1
is completed and the complete factual trajectory replays exactly.  Abstention
and failure are retained.  No repair, rerun, target substitution, or semantic
change is allowed after the first target is opened.

This is an outcome-heldout public-development batch, not a pristine hidden-game
claim: earlier census work exposed public observations.  Its purpose is to
detect broad reuse or brittleness before Kaggle evaluation.
