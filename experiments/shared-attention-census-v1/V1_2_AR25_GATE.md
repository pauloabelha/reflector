# Parallel Cognitive Workspace v1.2 — ar25 gate

This is a development gate, not held-out evidence. Its purpose is to decide
whether lossless structured ambiguity feedback closes one complete
Qwen→R2→environment control loop before any further census is attempted.

## Frozen run

- Game: `ar25`, fresh level-one start.
- Arms: fresh profile-matched `r2_only` and `shared_attention_qwen`.
- Profile: `balanced`.
- Action budget: 25 per arm.
- Qwen calls: action boundaries 0, 8, and 16 only; at most three.
- Qwen model/config and prompt are those in `config.json` at the checkpoint commit.
- Every graph event, request, response, action, transition, and replay boundary is durable.
- No prompt, controller, predicate, context, or policy change is allowed after launch.

## Pass condition

The shared arm must log one uninterrupted chain:

1. a Qwen proposal is criticized with concrete competing grounding witnesses;
2. a later, non-alpha-equivalent proposal or valid situated refinement cites that state;
3. R2 obtains one executable effect-pair binding;
4. the corresponding `grounds_pickup` edge is committed;
5. a `prior_used` decision differs from its same-state scratch recommendation;
6. the successor transition commits and a fresh ledger replay matches exactly.

Environment support is recorded only if the directly observed residual improves.
Task-score improvement is reported separately and is not implied by this mechanism gate.

## Stop conditions

- Success: stop after the first influenced successor passes exact replay.
- Ordinary failure: stop at action 25 if no complete chain exists.
- Hard failure: stop immediately on context/transport invalidity, forbidden leakage,
  support-authority violation, or replay mismatch.
- No fourth Qwen call and no in-run repair. A failure requires a separately
  preregistered v1.3 attempt; held-out games remain paused.

