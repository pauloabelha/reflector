# Parallel Cognitive Workspace v1.4 status

## 2026-08-09 — implementation preflight

- Frozen scope: one fresh paired real-ARC `ar25` level-1 gate, 48 actions per arm.
- No notes, frozen proposal, solution trace, or prior cognitive object is an input.
- Implemented live grounding alternatives, prospective predictions/probes, environment-only evidence, exact criticism lineage, alpha-novel Qwen revision, and confirmation-gated R2 control.
- Qwen receives current/recent visual frames plus the dependency-closed shared epistemic cut and ordered deltas.
- Durable recovery preserves exact Qwen requests, pending actions, prospective adjudications, and missing graph batches.
- Focused preflight: 16 tests passing; live environment not started yet.

## 2026-08-09 — terminal result

- Binary verdict: `INVALID` (transport-leakage guard, not a cognitive failure).
- `r2_only`: 48 actions, level 0, exact replay.
- `shared_live_qwen`: safely stopped at action 12 before its second prompt.
- Exact cause: `environment_evidence.payload.prospective.action_id` retained a raw
  opaque action field even though the linked prediction/action-proposal objects
  already carried a safe anonymous intervention reference.
- First live Qwen call itself succeeded and proposed
  `AlignedHorizontal(?a,?b) -> Decrease(TranslationAlignmentResidual(?a,?b))`
  at support zero. The invalid run cannot adjudicate the full causal gate.
- Correction is versioned separately as v1.5; these artifacts remain immutable.


## 2026-08-09 10:35:18 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- FAILED `generic_prospective/ar25/shared_live_qwen`: CognitionError: canonical graph projection leaks an action or game token.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=48, Q→R grounded=0, replay=True.
