# Shared Attention Census v1 — Live Status

Machine state is checkpointed after every epistemic event and real environment transition. This file records human-readable milestones.

## 2026-08-09 — Preregistration started

- Branch: `shared-attention-census-v1`, based on v0 result commit `74b5f42`.
- Scope: all 25 locally available public ARC games.
- Comparison: paired fresh-start `r2_only` versus `shared_attention_qwen`.
- Scientific priority: bidirectional cognitive pickup and grounded downstream work, not score maximization.
- Qwen server: existing local Qwen3-VL-4B Thinking server remains resident and is shared through one durable serialized request queue.
- No v1 ARC action has yet been executed.
- Pre-freeze clarification: every profile has its own fresh paired R2-only control; the frozen census is 150 episodes / 75 pairs, with at most 4,800 actions and 225 Qwen calls.

## 2026-08-09 — Pre-freeze implementation and smoke gates

- One authoritative epistemic graph, environment-only support, worker-specific frontiers, durable shared ledger, global FIFO Qwen queue, and fresh paired job matrix implemented.
- Direct-world interface added: Qwen receives current/recent PNG frames; graph regions carry frame, bounding-box, mask-RLE, and component grounding.
- Context compression added: short per-turn aliases, complete compact topology, dependency-closed full-payload cut, content-addressed R2 workspace expansions, and addressable visual history.
- Disposable real `ar25` R2 smoke: 3 committed actions, exact replay verified.
- First shared smoke diagnosed a 45,743-token projection and was discarded before freeze.
- Compact direct-vision shared smoke: 5,472 prompt tokens; valid strict Qwen response; one schema, one situated explanation, one attention write; 5 R2→Qwen pickups and 1 Qwen→R2 exposure; zero support authority changes; exact replay verified. The non-executable proposed potential remained epistemic.
- Verification: v1 25/25 tests and repository 77/77 tests passed; Python compilation and diff check passed.
- No frozen v1 census action has yet been executed.

## 2026-08-09 00:50:54 — live census launched

- Jobs: 150; games: 25; profiles: 3; environment workers: 4.

## 2026-08-09 00:53 — run stopped at the second-turn anonymity gate

- `balanced/ar25/shared` stopped before its t=8 Qwen request because the graph field `eligible_action` matched the action-token leakage guard.
- This was transport metadata for proposal expiry, not an ARC action value, but the frozen gate correctly rejected it. No leaking request reached Qwen.
- The coordinator was stopped rather than allowing an invalid 150-job matrix to continue.
- All partial ledgers were preserved under `artifacts-aborted-05ea3ca-20260809-0053/`.
- Generic correction: renamed the graph-visible field to `eligible_step`; no game-specific prompt, schema, controller, or policy change.
- Follow-up t=8 smoke exposed and fixed two generic compact-delta defects: the response-schema reader expected verbose events, and the exact 96-event JSON rendering exceeded 8K context.
- Final compression uses stable content-derived aliases plus ordered opcodes. Non-frontier dormant runs retain order range, kind counts, and hash while exact events remain expandable in the authoritative ledger.
- Final 9-action/two-turn real smoke: both Qwen replies valid, six accepted writes, prompt sizes 5,474 and 5,658 tokens, zero transport errors, exact replay, and bidirectional pickup. Both non-executable potentials remained safely epistemic.
- FAILED `balanced/ar25/shared_attention_qwen`: CognitionError: canonical graph projection leaks an action or game token.

## 2026-08-09 01:02:22 — live census launched

- Jobs: 150; games: 25; profiles: 3; environment workers: 4.
- COMPLETE `balanced/ar25/r2_only`: levels=0, actions=32, Q→R grounded=0, replay=True.
- COMPLETE `balanced/ar25/shared_attention_qwen`: levels=0, actions=32, Q→R grounded=0, replay=True.

## 2026-08-09 01:19 — balanced pilot stopped at the ar25 development gate

- Preserved the complete stopped run under `artifacts-pilot-78edacb-20260809-0119/`; two ar25 jobs completed and four in-flight jobs retain action-by-action checkpoints.
- `balanced/ar25` was an exact replay-valid 32-action failure in both arms. The shared arm made three valid Qwen calls and recorded five R2→Qwen plus three Qwen→R2 exposures, but zero grounded pickups and zero changed actions.
- All three calls repeated `SameArea(?a,?b) -> Decrease AreaDifference(?a,?b)`. R2 could not execute that potential, but its rejection never reached Qwen; false situated bindings were accepted; repeated semantics received new IDs; and later cuts remained pinned to stale initial entities.
- The full R2 state was still reachable only through an opaque blob rather than as traversable first-class objects. This violated the v1 shared-cognition invariant, so the remaining 148-job census was stopped instead of spending an estimated additional 8–10 hours on invalid evidence.
- Repair is restricted to the designated ar25 development gate: materialize R2 cognition, expose correspondence history, return structured criticism, deduplicate semantic claims, validate situated conditions, align executable DSL semantics, and improve exact/small-lossy context coding. Held-out census remains paused until ar25 succeeds.
- Four already-running worker threads finished additional obsolete pilot work after the coordinator interrupt; that tail is separately preserved under `artifacts-pilot-tail-78edacb-20260809-0141/` and will not be mixed with the replacement gate.

## 2026-08-09 — v1.1 ar25 repair checkpoint

- R2 schemas, bindings, partial bindings, shadows, explanations, and exact workspace snapshots are first-class addressable graph objects. Unresolved internal term→pixel links are explicit `OPEN` ports rather than false groundings.
- Frame-to-frame component correspondences are first-class and transition-linked. Qwen explanations are condition-checked against visible descriptors/relations; repeated semantic claims deduplicate while response derivations remain durable.
- R2 grounding failures now return structured zero-support criticism before the next Qwen turn is queued. Only directly observed residual improvement can create environment-authored support.
- Context transport preserves all 272 initial ar25 objects in a columnar topology, renders the triad/relation packet in full, projects large masks by stable digest, and uses explicitly small-lossy hash/count summaries only for dormant event runs whose exact bodies remain authoritative.
- Measured local-Qwen prompt: 12,865 tokens including vision and JSON grammar. The resident server now uses a 16,384-token context (3,750 MiB projected GPU allocation); a 1,549-token completion produced a valid strict response with no transport error.
- Verification before the replacement real-game gate: v1 34/34 tests and repository 77/77 tests pass; Python compilation and diff check pass.
