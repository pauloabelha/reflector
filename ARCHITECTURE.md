# Architecture

Reflector has one inference core and several consumers.

```text
reflector.SymbolicPolicy
  ├── official Agent adapter ── official Swarm/Arcade ── local runs
  ├── generated Kaggle overlay ── official starter ── Kaggle gateway
  ├── experiment runner ── transformed traces + SQLite
  ├── population evaluator ── sandbox + Pareto archive
  └── replay API ── browser-native TypeScript analysis console
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

`AbstractionStore` performs three bounded reflection passes after transition
learning. It groups cross-context schemas by action/result predicates, groups
synthetic concepts by evidence-backed kind, and detects rotation vocabularies
that can be represented by an orientation algebra. It retains only
description-positive structures and records their evidence, residual cost, and
language ancestry. The store is part of the shared Kaggle closure.

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

The Kaggle closure contains symbolic values, perception, schemas, reflecting
abstraction, causal and temporal hypotheses, planning, dependency graphs, mind,
policy, and trace types. Evaluation, compression analysis, transforms,
experiment persistence, population selection, mutation providers, sandbox
orchestration, evolver, and CLI modules remain outside it.
Future inference mechanisms must be added to the explicit overlay allowlist
and pass its import closure test.

## Development control plane

`MindConfig` is the deployable genome. It contains bounded booleans, planner
limits, and action-selection weights, has a strict JSON representation, and is
constructed by `SymbolicPolicy` on every execution surface. There is no
research-only organism.

`ExperimentManifest` hashes source traces and holdout seeds into a stable
experiment identity. `ExperimentStore` keeps candidates, parent links,
fitness, and detailed results in local SQLite. `MutationProvider` is a narrow
interface: deterministic or optional remote providers return one structured
configuration patch. Validation rejects unknown fields, compound values, and
out-of-range settings before execution.

`validate_candidate` starts a fresh interpreter with a clean environment and,
by default, a disabled Linux network namespace. It executes the candidate
twice over the original and color-permuted traces and rejects nondeterminism.
The Pareto archive maximizes level evidence, replay retention, and schema
reliability while minimizing planner expansions and description length.

This control plane depends on the inference core. None of it is packaged in
the Kaggle overlay, and the import-closure test permanently enforces that
direction.

## Replay and analysis surface

`reflector.web_api` deterministically reconstructs the deployed policy at each
recorded observation. Its loopback HTTP server exposes the replay bundle,
configuration branches, experiment manifests, candidate metrics, lineage, and
Pareto membership. It serves the compiled `web/` application from the same
origin and makes no outbound calls.

The frontend is strict TypeScript compiled to browser-native modules, with no
runtime framework or CDN. Board playback, symbolic inspectors, graphs,
genealogy, candidate diffs, regression summaries, and the Pareto plot are all
derived from API evidence rather than fixture-shaped dashboard data.

A trace branch changes only a validated `MindConfig` and replays the complete
recorded prefix before displaying the selected suffix. Since the observations
remain fixed, the API labels the result `trace-only-policy-branch` and does not
claim alternate game dynamics or score. A future environment-snapshot adapter
is required for causal branch-and-rollout.
