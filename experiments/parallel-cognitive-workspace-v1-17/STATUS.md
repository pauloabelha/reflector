# Parallel Cognitive Workspace v1.17 status

## 2026-08-09 — preregistered before selected-game perception

- Frozen parent: `77bc32cdb489b43c6cfa4787cc4cff8d95b30d61`.
- Initial preflight rejected an all-game selector because its winner `tu93` has
  `keyboard_click` metadata, outside the frozen simple-keyboard transport
  contract. No environment had been opened.
- The corrected metadata-only eligibility rule (`tags == ["keyboard"]`) plus
  the frozen parent-commit hash selected `wa30` with score
  `6b6a120480452cdcf70bfc74a113ff38f44f003f591816b9e4e8b1e1bf8bb6bf`.
- No v1.17 environment has been opened and no selected-game frame has been
  perceived at this checkpoint.

## 2026-08-09 13:46 — frozen paired run

- Both fresh arms began from digest
  `3221ce21d1ff7a1bdae598971571fed48317866e3a2125b8693d63a86cab340a`.
- R2-only and shared-live-Qwen both stopped unsolved at 64 actions with the
  same action sequence and final digest
  `1d84449983eea49d5c338bc965502f53c53d1f3de50d8d62f1d0da64c878f430`.
- Both factual trajectories replayed exactly. The shared arm completed all four
  Qwen transports and compilations with valid context, zero transport errors,
  and zero support-authority violations.
- The first two Qwen turns produced no executable schema. The third produced
  `AlignedHorizontal(?a,?b) -> Decrease TranslationAlignmentResidual(?a,?b)`.
  R2 uniquely grounded it to `f00/f05`, creating one Qwen-to-R2 grounded
  pickup, but no local action model predicted a useful consequence for that
  binding. It therefore received no prospective support or confirmation and
  never changed control. The fourth turn did not create the missing causal
  chain.
- The shared arm created 200 prediction objects but zero supported predictions,
  zero evidence-citing revisions, zero confirmed revision bindings, zero prior
  decisions, zero changed actions, and zero counterfactual branches.
- `artifacts/SUMMARY.json` reports a valid `FAIL`: every validity gate passes,
  but all six required transplant-chain gates are false. Level completion was
  also zero in both arms.

## 2026-08-09 13:46:34 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- COMPLETE `generic_prospective/wa30/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
- COMPLETE `generic_prospective/wa30/shared_live_qwen`: levels=0, actions=64, Q→R grounded=1, replay=True.
