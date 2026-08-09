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
