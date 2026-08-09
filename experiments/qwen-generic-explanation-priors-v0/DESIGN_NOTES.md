# Design Notes

## What this experiment tests

Qwen receives a bounded anonymous relational snapshot and may select a schema instance from a closed, generic R2 hypothesis language. It does not invent new executable predicates in v0. A positive result therefore means that an external explanation proposer can help select and connect R2 concepts—not that language alone solved a game.

R2 owns every safety-critical step: syntax validation, alpha-normalization, relation verification, target grounding, local opaque-action calibration, control, and outcome measurement. An accepted Qwen proposal starts with zero evidence and cannot influence an action until a real target transition confirms an action-relative centroid consequence.

## Generic controller

Each uniquely grounded effect pair tracks its doubled-centroid relative vector. For every opaque simple action, the controller learns the modal change in that relative vector from direct visible correspondences. It may then choose a locally confirmed action only when the predicted next residual changes in the proposal's preferred direction. Otherwise it executes the exact scratch fallback: least used action, then smallest opaque ID.

When a pair becomes occluded, R2 may project a directly observed action delta for at most four steps. Projections affect control state but never increase empirical support. On reappearance, new evidence is measured from the visible predecessor frame, not from the latent forecast.

## External versus self-built provenance

- `qwen_own`, `qwen_mismatch`, and `human_reference`: `externally-proposed`.
- `self_built_reference`: `transferred-self-built` from the earlier chronological ar25 induction experiment.
- A Qwen binding with direct target evidence additionally reports `externally-proposed-and-locally-confirmed`.
- Scratch contains no schema binding.

The two ar25 reference arms are diagnostics. They do not count toward the primary generic-prompt cross-game verdict.

## Crash and contamination controls

Every arm has private recording, trace, checkpoint, progress, and result paths. Before each environment step, an atomic checkpoint commits the exact predecessor digest, action ID/data, and decision provenance as `pending`. After the successor is perceived and learned, a second atomic replace appends the transition and clears `pending`. Atomic writes fsync both file and parent directory.

A resume creates a fresh environment, replays the committed ledger while checking every predecessor and successor observation digest, then deterministically rebuilds the controller from the frozen proposal and transition history. A completed arm is replayed once more from a fresh environment. Any mismatch aborts rather than silently restarting.

Qwen is called exactly once per selected game before live play. Its prompt is byte-identical across games; only the appended anonymous state differs. Responses are never repaired after inspection. Invalid output becomes abstention. The frozen manifest hashes code, prompt, configuration, cohort, states, raw responses, and compiler decisions before any live target action.
