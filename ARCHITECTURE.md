# Architecture

Reflector has one inference core and several consumers.

```text
reflector.SymbolicPolicy
  ├── official Agent adapter ── official Swarm/Arcade ── local runs
  ├── generated Kaggle overlay ── official starter ── Kaggle gateway
  ├── experiment runner (future)
  ├── population evaluator (future)
  └── replay API/UI (future)
```

`Observation` and `Decision` are immutable protocol values. `SceneTracker`
extracts same-color connected components, assigns episode-persistent identities,
and derives typed facts and events. `SchemaStore` accumulates empirical
context + action → result schemas with Beta-smoothed reliability and action
attribution. `ConceptStore` compiles repeated reliable effects into synthetic
concepts only when measured utility exceeds description complexity.

`SymbolicMind` owns this online state and balances predicted utility against an
information bonus. `HypothesisStore` compares action-effect rates against
observed controls, records one-step temporal regularities, and produces
explicit information-seeking questions. `SymbolicPlanner` performs bounded
search over learned event operators toward the current `level_advanced` goal
and reports every expansion. Its proposal is one scored input to action
selection, not an unbounded side channel.

`EpisodeTrace` records the same scenes, transitions, hypotheses, experiment
questions, plans, decisions, and concept births used during inference. Replay,
compression analysis, and evaluation consume those records without a parallel
agent implementation.

The Kaggle artifact is an overlay, not a fork. It contains the shared package,
the thin adapter, and a minimal agent registry. The notebook extracts those
files over the competition-provided official starter and invokes its `main.py`.

Development-only systems will depend inward on the symbolic package. The
symbolic package must never depend outward on an evolver, LLM, trace analyzer,
SQLite store, API server, or frontend. `tests/integration/test_kaggle_contract.py`
enforces the current inference closure.

The Kaggle closure contains symbolic values, perception, schemas, causal and
temporal hypotheses, planning, dependency graphs, mind, policy, and trace
types. Evaluation, compression analysis, and CLI modules remain outside it.
Future inference mechanisms must be added to the explicit overlay allowlist
and pass its import closure test.
