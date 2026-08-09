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
