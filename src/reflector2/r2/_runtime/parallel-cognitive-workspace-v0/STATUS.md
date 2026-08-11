# Parallel Cognitive Workspace v0 — Live Status

Human-readable milestones are appended here. Machine state is written after every workspace event and every real environment transition.

## 2026-08-08 — Start checkpoint

- Branch: `parallel-cognitive-workspace-v0`, based on successful Qwen-prior result tip `394285e`.
- Experiment root: `experiments/parallel-cognitive-workspace-v0/`.
- Regression source: frozen ar25 Qwen-own result from `qwen-generic-explanation-priors-v0` (17 actions, one completed level, replay verified).
- Architecture: independent fast R2 loop and persistent slower Qwen worker communicate through one versioned, durable, hash-chained epistemic workspace.
- Authority boundary: both processes may propose schemas/explanations/questions/experiments; only chronological environment transitions contribute confirmation or refutation, and only the environment arbiter may commit actions.
- Development gate: reproduce the ar25 result through the workspace before freezing architecture.
- Held-out evaluation after freeze: `cd82`, `wa30`, and negative control `cn04`.
- Qwen server policy: keep the existing local server GPU-resident; do not stop it after the experiment.
- Current phase: preregistration and implementation. No new ARC action has been executed.

## Recovery policy

- One immutable atomic event file per workspace revision, plus a hash-chained atomic `HEAD.json`.
- Independent R2, Qwen, and arbiter cursors.
- Exact pending→committed action checkpoints and fresh-environment ledger replay.
- Qwen requests and responses content-addressed and basis-revision tagged; stale outputs remain auditable but cannot silently mutate control.

## 2026-08-08 — Development gates and live interface diagnosis

- Offline chronology gate passed: two byte-identical 17-transition workspace replays, every prefix resumed to the same final state, and one historical ar25 level completion.
- Real frozen-proposal compatibility gate passed: ar25 level 1 completed in 17 actions with exact sequence `1, 2×11, 3×5`; 14 prior-guided decisions were locally confirmed and the final environment replay was exact.
- Live parallel attempt with a 360-token output cap reached the 32-action budget without a bound proposal. All four Qwen calls ended inside reasoning with empty content; the complete failed workspace is preserved under `artifacts/development-runs/token-cap-360/`.
- The cap was corrected to the preregistered 900 tokens and the successful one-shot experiment's 256-token thinking setting. All 14 focused workspace/protocol/worker tests still passed.
- Live parallel attempt with the 900-token cap again reached 32 actions with exact replay and no admitted proposal. Three calls truncated while trying to emit all four cognitive-object types; one completed response proposed the useful generic schema `SameOutline(?a,?b) -> Decrease(TranslationAlignmentResidual(?a,?b))` but was correctly rejected for exceeding the two-write cap.
- Current diagnosis: concurrency, durability, causal release, and grounding paths work; the initial Qwen write grammar is too broad for a compact 4B-model turn. Next development revision is a generic phased grammar that exposes only currently legal object types and never manufactures placeholder references. Held-out games remain untouched.

## 2026-08-08 — Phased live-workspace result

- Replaced the broad grammar with a sparse phase-specific protocol. Inactive write types are absent rather than encoded as unsupported zero-length arrays; ambiguous/unbound schemas remain visible for later refinement. Experiment tests pass `16/16`; the repository suite passes `77/77`.
- Same-workspace no-Qwen control failed at 32 actions with the deterministic six-action cycle and exact replay.
- Final live parallel run made four valid causal-prefix Qwen calls at action bases `0, 4, 8, 12`. R2 and Qwen overlapped in real time; every request/reply/adjudication/action was durably checkpointed.
- Qwen's schema sequence was: (1) a three-figure SameOutline hypothesis, ambiguous; (2) a SameOutline/SameArea/SameInteriorLayout triad refinement, ambiguous; (3) an AlignedHorizontal refinement, unbound; (4) a SameOutline/SameInteriorLayout refinement, ambiguous.
- No external schema obtained a unique binding, no Qwen proposal influenced an action, and the live arm matched the 32-action no-Qwen failure. Final environment replay was exact.
- Development verdict: `GATE_FAILED_WITH_SCHEMA_PROGRESSION`. Frozen-proposal compatibility remains positive (17 actions), but the live workspace did not reproduce it. Held-out `cd82`, `wa30`, and `cn04` were not opened.
- Identified next interface requirement: emit compact R2 adjudication deltas containing anonymous competing groundings/rejection witnesses, and make historical motion predicates genuinely groundable. The current workspace exposes only `ambiguous`/`unbound`, even though Qwen receives motion relations. This is the smallest principled follow-up; no further ar25 tuning was performed in this experiment.
