# Progress log

## 2026-08-03 — Milestone 1

- Read the complete project specification.
- Found the requested fresh repository empty.
- Located old infrastructure at `~/reflector_old` (underscore, not hyphen).
- Preserved only the official adapter/offline packaging contract.
- Froze the clean-room architecture, minimal terminology, DSL 0.1 semantics,
  firewall, assumptions, parallel transaction, and claim boundaries.

Capability demonstrated at this checkpoint: documentation only. Runtime
capabilities are recorded here only after tests pass.

## 2026-08-03 — Vertical slice and deterministic acceleration layer

- Implemented the typed AST, checker, canonical serializer, interpreter,
  audited S0 registry, composition/products, quote/eval, diagrams, complexity,
  rewrites, analogy validation, firewall, and immutable serialized Mind.
- Implemented pure `CandidateInput -> CandidateResult` evaluation with derived
  worker seeds, serial/process modes, stable ranking, coordinator-only commit,
  source/Mind/config manifests, and explicit boundaries for all requested
  parallel work classes.
- Implemented legal runtime policy, action budget, synthetic causal failure,
  exact replay, direct DSL traces, dashboard indexing/rendering, official-agent
  adapter scaffold, deterministic overlay, and smoke test.
- Benchmarked 32 tiny candidate tasks: serial 0.001542 s vs two-process 0.011145
  s. Kept serial as default and set the generic process threshold to 64 tasks.

Demonstrated: the synthetic run selects legal actions, detects a failed causal
prediction, validates a rewrite, and replays exactly. This does not demonstrate
ARC-AGI-3 competence. Hidden transfer, automatic learning stages, and useful
GPU batching remain unproven.

## 2026-08-03 — Live dashboard acceptance

- Added a flushed append-only JSONL trace sink and canonical replay finalizer.
- Added a live synthetic source that starts on first view and invokes the same
  runtime episode/policy path as replay.
- Added synchronized frame/action/schema/candidate/prediction/metric/update
  views, activation graph, raw event inspector, timeline, previous/single-step,
  play/pause, and speed controls.
- Added exact live/replay event and scientific-step equivalence tests.
- Exercised the localhost HTTP page and API: six events, two steps, actions
  `[2, 1]`, no server/runtime error, and exact saved-replay equality.

The UI is read-only. Its pause control freezes presentation for inspection and
does not pause or alter agent decisions.

## 2026-08-03 — Executable developmental loop

- Replaced retrospective prediction scaffolding with typed `observe`,
  `predict`, `compare`, and `evidence_update` interpreter operations.
- Replaced the two-step mock with a three-transition environment: one grounding
  transition, one prediction confirmation, then one controlled violation.
- Added coordinator-validated evidence updates and rewrite commits.
- Added pure competing rewrite evaluation using serial or process workers,
  stable ranking, completion-order-independent reduction, and derived seeds.
- Connected the dashboard to real evidence, diagram, rewrite-candidate, and
  committed Mind events; removed reliance on placeholder update fields.
- Verified the live and replay HTTP APIs over the same 18 canonical events.

Demonstrated evidence ends at two attempts, one confirmation, one failure, and
confidence 0.5. The failed diagram triggers a rewrite that is evaluated without
Mind mutation, then committed by revoking the old identifier and adding the
deterministically identified replacement.
