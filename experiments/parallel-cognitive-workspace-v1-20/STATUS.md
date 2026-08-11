# Parallel Cognitive Workspace v1.20 status

## 2026-08-09 — preregistered two-tier frontier

- v1.18 and v1.19 are preserved as `INVALID` capacity runs.
- Optional attention remains bounded at 6,400 units.
- Mandatory exact truth may expand only to its measured requirement, with a
  frozen hard ceiling of 14,000 units.
- Every cognitive request receives an exact server-side multimodal admission
  count with a 512-token safety margin; the one-token output is discarded.
- No semantic/controller/prompt/compiler/schedule/action-budget/gate change.
- No fresh v1.20 environment has been opened yet.

## 2026-08-09 14:28:23 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- FAILED `generic_prospective/wa30/shared_live_qwen`: CausalPacketError: original ambiguity diagnosis is unavailable.
- COMPLETE `generic_prospective/wa30/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
