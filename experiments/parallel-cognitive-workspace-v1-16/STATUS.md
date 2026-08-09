# Parallel Cognitive Workspace v1.16 status

## 2026-08-09 — implementation

- v1.15 factually completed ar25 level 1 in 38 actions versus an unsolved
  64-action R2-only control, but failed while persisting its post-episode
  counterfactual result.
- v1.16 changes only the ledger event allowlist. No fresh v1.16 ARC environment
  has been opened and no fresh-workspace Qwen request made.

## 2026-08-09 — isolated counterfactual checkpoint

- The completed v1.15 shared workspace was copied to an isolated temporary
  audit root and evaluated through the v1.16 ledger repair. The original
  workspace was not modified.
- All eight recorded Qwen-influenced control decisions produced durable
  `CounterfactualBranchVerified` events.
- All eight factual branches replayed to their recorded successor digests.
- All eight Qwen-selected actions were favorable to the recorded same-state
  fallback under the preregistered translation-alignment residual:
  `72<78`, `66<72`, `60<66`, `54<60`, `48<54`, `42<48`, `36<42`, and `30<36`.
- This verifies the causal control segment of the v1.15 factual breakthrough,
  but it is not substituted for the required fresh v1.16 paired run.
