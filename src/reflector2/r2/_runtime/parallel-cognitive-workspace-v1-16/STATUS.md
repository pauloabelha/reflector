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

## 2026-08-09 13:27:23 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
- COMPLETE `generic_prospective/ar25/shared_live_qwen`: levels=1, actions=38, Q→R grounded=2, replay=True.

## 2026-08-09 — fresh paired result: PASS

- Both arms began from observation digest
  `8c9c38b5c049817e37ea6525b513983e3628a3f1224df5eafb3146175bb2a51b`.
- The fresh R2-only control did not complete level 1 within 64 actions.
- The fresh shared live-Qwen arm completed level 1 in 38 actions.
- Four Qwen calls completed with four valid compilations, zero transport errors,
  valid context admission, and zero support-authority violations.
- Qwen's initial schema grounded ambiguously to three effect pairs. R2 ran four
  prospective probes and returned environment evidence through the shared
  workspace. An alpha-equivalent revision was rejected and surfaced as
  compiler criticism. A subsequent non-alpha revision selected the unique
  `f01/f02` pair through `SameInteriorLayout` and was prospectively confirmed.
- The confirmed revision changed 13 control decisions and accumulated 18
  environment-authored support edges. The selected pair's alignment residual
  was driven to completion.
- Both factual trajectories replayed exactly. All eight audited same-state
  counterfactual branches replayed exactly, and all eight Qwen-selected actions
  improved the preregistered residual relative to fallback:
  `72<78`, `66<72`, `60<66`, `54<60`, `48<54`, `42<48`, `36<42`, and `30<36`.
- `artifacts/SUMMARY.json` reports `binary_gate.verdict = "PASS"`; every outcome,
  causal-chain, and validity gate is true, with no failures or cancellations.
