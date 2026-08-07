# Architecture decision record: clean Schema Calculus vertical slice

Status: accepted for milestone 1. Date: 2026-08-03.

## Decision

Reflector is rebuilt around one immutable, serializable `Schema[A, B]` AST.
Concepts are quoted schemas, procedures are evaluated schemas, causal models
are schemas over context/action products, strategies are higher-order schemas,
and rewrites and analogies are typed data about schemas. There is no embedded
Python escape hatch. Native operations live in an audited registry.

The fixed engine, learned Mind, runtime, evaluation, dashboard, and Kaggle
adapter are separate packages. A run always uses the same `RuntimePolicy` and
serialized Mind. Submission code is only an interface adapter.

## Clean-room boundary

`../reflector_old` was inspected only for reusable infrastructure: the official
`Agent.is_done(frames, latest_frame)` and `choose_action(frames, latest_frame)`
contract, `FrameData`/`GameAction` conversion, competition-provided wheels,
offline execution, and deterministic overlay expectations. Old policy logic,
schema libraries, candidates, identifiers, game heuristics, and representations
are deliberately excluded as contaminated architecture.

The requested `~/reflector-old` path did not exist; the available source was
`~/reflector_old`.

## Deterministic candidate transaction

```text
immutable Mind snapshot
  -> pure candidate generation
  -> CandidateInput -> CandidateResult (serial or process pool)
  -> collect all results
  -> stable sort by (loss, complexity, candidate_id)
  -> coordinator validates and commits one transaction
  -> serialize the new immutable Mind
  -> coordinator returns the legal action
```

Workers never mutate the Mind, assign committed identifiers, or select the
action. Worker seeds are SHA-256 derivations of `(run_seed, candidate_id)`.
Completion order has no semantic effect. Multiprocessing is optional and is
disabled below a configured task-count threshold; a benchmark helper measures
whether overhead justifies enabling it. Array/batch-shaped primitive inputs
are exposed without making GPU execution a dependency.

`parallelism.TaskBoundary` defines the common immutable boundary for candidate
evaluation, schema grounding, composition/rewrite alternatives, independent
game/level/seed/ablation replay, confidence/loss terms, analogy correspondence,
primitive-closure checks, rewrite regression, trace indexing, and offline
reports. Each subsystem supplies a pure worker for its task kind and returns a
`TaskResult`; `stable_results` erases completion order before coordinator
reduction. Version 0.1 exercises this backend concretely for candidate schemas;
the remaining kinds have an explicit contract but no unearned capability claim.

## Assumptions and compromises

- Python 3.11+ is available locally and on the target notebook.
- The exact upstream ARC packages may be absent during unit tests; the adapter
  imports them lazily while its pure policy facade remains testable.
- The current milestone implements the complete executable vertical slice and
  a deliberately small subset of the long-term operation catalogue. Unbuilt
  constructs are documented as reserved, never presented as working.
- Synthetic progress demonstrates invariants, not ARC skill.

## Demonstrated / unproven

Tests demonstrate deterministic serialization, typed execution, quote/eval,
causal failure, explicit rewrite regression, legal actions, replay, exact trace
indexing, local/submission identity, and serial/process semantic equivalence.
Hidden-game competence, useful analogy transfer, automatic compression,
learned S0 extension, and GPU acceleration remain unproven.
