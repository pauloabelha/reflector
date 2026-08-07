# Deterministic vertical-slice audit

Baseline audited: 2026-08-03, before the developmental-loop implementation.

## Exact baseline gates

```text
python3 -m pytest -q
25 passed

/home/pauloabelha/reflector_old/.venv/bin/ruff check .
All checks passed!

PYTHONPATH=/home/pauloabelha/reflector_old/.venv/lib/python3.12/site-packages \
  python3.12 -m mypy schema_calculus mind runtime learning evaluation \
  dashboard submission parallelism
Success: no issues found in 43 source files
```

Passing these tests did not prove the newly requested loop. The gaps below were
found by following executable calls and trace producers rather than file names.

## Complete and tested at baseline

- Primitive/product types, immutable `Schema`/`ReifiedSchema`, identity,
  sequential/parallel composition, quote/eval, checker, interpreter, canonical
  serialization, and complexity accounting execute deterministically.
- Action candidates use immutable `CandidateInput -> CandidateResult`, stable
  ranking, derived worker seeds, and coordinator-only Mind additions.
- Serial/process action evaluation selects the same action and serialized Mind.
- Runtime action selection enforces exposed legal actions and the separate
  `ActionBudget` fails closed.
- Submission facade calls `RuntimePolicy`; local/submission action identity is
  tested for one state. The optional official adapter matches the closest
  inspected `Agent.choose_action` boundary but has not run against Kaggle.
- Dashboard live JSONL and replay JSON contain identical canonical events; the
  browser is read-only and does not call policy code.

## Partial components

- `guard` exists in checker/interpreter/complexity but has no direct unit test.
- Schema records serialize attempts, confirmations, failures, and confidence,
  but no runtime transaction updates them.
- Generic difference and action-conditioned primitives execute, but the causal
  projection in the synthetic episode is computed after the actual transition.
- A prior observed delta is displayed as the next prediction and can fail, but
  the episode has no controlled prediction success before that failure.
- Diagram comparison detects a mismatch, but its event is assembled in the
  replay harness rather than through explicit compare semantics.
- A rewrite value and regression validator exist, but the live Mind is neither
  protected during candidate evaluation nor changed by a rewrite transaction.
- Candidate parallel equivalence is tested for action selection only, not
  rewrite ranking or completion-order independence.

## Placeholders, mocks, and disconnected surfaces

- `observe`, `predict`, `compare`, and explicit evidence update are prose or
  harness operations, not typed DSL nodes.
- Dashboard `schema_reifications`, `confidence_updates`, and
  `primitive_proposals` are emitted as empty tuples. `schema_rewrites` is empty
  on action/transition events and later populated by a noncommitting validation
  event. These fields therefore do not yet evidence developmental semantics.
- `post_observation_projection` is retrospective and must not be presented as
  a pre-action prediction.
- Analogy and primitive-extension modules are not on the vertical-slice runtime
  path. They are retained but are not evidence for this milestone.
- Generic parallel task-kind declarations other than action candidates are
  contracts only, not active workers.

## Policy, trace, and determinism risks

- There is one action-policy path, but episode-level causal prediction,
  comparison, diagram creation, and rewrite validation are separate harness
  logic. The milestone requires these to execute as schemas and coordinator
  transactions while still emitting the same append-only trace.
- Process collection is stably sorted, but completion-order independence has
  not been exercised for competing rewrites.
- `verify_replay` reruns inference to test determinism; dashboard replay itself
  correctly loads events without inference. A dedicated trace-identity test is
  still required for identical initial Mind, observations, and seed.

## Kaggle assumptions

- `arcengine`/official starter packages are not part of the fresh repository's
  default test environment. `build_official_agent_class` is therefore an
  explicit lazy boundary, not live Kaggle verification.
- The deterministic overlay excludes `dashboard`, but this needs an explicit
  dependency/zip-content test.
- The submission facade uses single-process action selection, which is the
  intended Kaggle semantic baseline.

