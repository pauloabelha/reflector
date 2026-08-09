# Parallel Cognitive Workspace v1.18 status

## 2026-08-09 — implementation before fresh v1.18 environment

- Development target: wa30, following the valid v1.17 no-calibration failure.
- Added only generic unique-binding opaque-action calibration and one later
  evidence-reading Qwen boundary.
- No v1.17 workspace, response, schema, binding, model, or action history will
  seed the fresh v1.18 workspaces.

## 2026-08-09 14:09:47 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- FAILED `generic_prospective/wa30/shared_live_qwen`: FrontierBudgetError: frontier budget 6400 is below mandatory closure cost 9843.
- COMPLETE `generic_prospective/wa30/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
