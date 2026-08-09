# Frozen cross-game progress-goal test v1

This test applies the exact v5 semantic prompt, workspace projection, compiler,
open-port grounder, calibration prefix, and controller to one mechanically
selected non-wa30 game. No frame/source/outcome is inspected during selection.

Candidate universe: installed environments with exactly one metadata file and
metadata tags exactly `["keyboard"]`, excluding the consumed development game
`wa30` and source development game `ar25`. Rank by SHA-256 of
`reflector2-v1.16-heldout-simple-action-selector-v1\0` plus the directory game ID; choose the
lexicographically smallest digest. The frozen result is `g50t` version
`g50t-5849a774`.

The selection receipt is written and fsynced before the environment is opened.
The run is fresh and empty. PASS requires level1 within 40 actions and exact
replay. A valid unsupported goal family, absent structural grounding, or no
completion is FAIL—not grounds to switch games or edit the architecture.

This game appeared in earlier broad censuses, so it is an unchanged fresh
cross-game instance test, not a pristine never-seen/Kaggle claim.
