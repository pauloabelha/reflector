# Architecture

Reflector has one inference core and several consumers.

```text
reflector/
├── core/       deterministic symbolic state, learning, and planning
├── runtime/    deployed policy, configuration loading, and traces
├── research/   evaluation, diagnostics, transforms, and validation
├── evolution/  candidates, mutations, persistence, and sandboxing
├── cli.py      local command-line composition root
├── kaggle.py   offline overlay exporter and compatibility verifier
├── web_api.py  local replay/analysis composition root
└── *.py        compatibility imports for the pre-reorganization API
```

Dependencies point inward: `core` imports only `core`; `runtime` may import
`core`; `research` may import `runtime` and `core`; and `evolution` may import
the other three. Architecture tests enforce this direction. Top-level
compatibility modules preserve established `reflector.mind`,
`reflector.policy`, and related imports while new code uses the canonical
package paths.

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

`AbstractionStore` performs bounded compilation passes after transition
learning. It groups cross-context schemas by action/result predicates, groups
synthetic concepts by evidence-backed kind, detects rotation vocabularies that
can be represented by an orientation algebra, and compiles repeated successful
trajectories into procedures. It retains only description-positive structures
and records their evidence, residual cost, and language ancestry. Retained
concepts compile into future schema contexts, accepted language operators
normalize future events, family reliability informs transfer, and procedures
can supply bounded plans. The store is part of the shared Kaggle closure.

The language inducer is itself represented inside that store. Its rejected and
accepted proposals, parented revisions, evidence, complexity utility, and
retained products are serialized into traces and dependency graphs. This is a
bounded meta-reflective mechanism, not arbitrary runtime code generation.

`StructuralCreditLedger` compares each proposition-level schema prediction
with the next outcome before that outcome updates the schema store. It keeps
external goal events, epistemic events, confirmations, contradictions, and
unpredicted effects as typed fields and carries a bounded eligibility trace
that names both proposition and licensing schema. This prevents hindsight
scoring and preserves the evidence needed for later accommodation. The ledger
constructs MDL-positive conditional proposition amendments from repeated
disequilibria, retains their evidence and history, and makes applicable
goal-relevant amendments operative in action selection. Validation v3 shows a
causal effect for this narrow mechanism under one synthetic perturbation
family. It does not yet modify planning or justify a claim of general
equilibration.

`TransformationSystem` reflects repeated movement schemas into MDL-positive
translation operators. After level-advance evidence grounds adjacency as an
operative goal, a bounded breadth-first planner composes those operators in
future layouts. Validation v4 shows a causal control effect for this narrow
composition mechanism on one synthetic family. It also represents observed
inverse partners and can exhaust a finite bounded state graph for calibrated
possible/impossible reachability. Frame bounds are perceived facts, and an
expansion cap yields `unknown`, never an impossibility claim. Validation v5
shows that this exhaustive distinction causally improves control when possible
goals exceed the ordinary short-planner horizon. This remains bounded spatial
reachability, not general modal logic.

The higher-order substrate keeps two explicitly separate structures. The
transformation set contains state-changing operators and executable temporal
composition. The comparison graph contains typed mappings between
transformations and structural composition of compatible mappings. Its finite
endpoint, identity, closure, and associativity checks pass, but these laws are
structural evidence only: those generated morphisms do not improve action
selection. A separate `ComparisonTransferSystem` now learns context-typed
operators directly from perceived domains, accepts a finite square-symmetry
map only when at least two non-collinear correspondences identify it uniquely,
and keeps source, calibration, comparison, and observed/inferred provenance.
Validation v6 shows that applying such a direct comparison causally improves
synthetic held-out control and that inconsistent calibration causes
abstention. Perceived marker components can act as comparison-link tokens: a
bridge domain may share one token with its source and another with its target.
The system can propagate an operator through at most three comparisons,
retaining the ordered comparison path and accepting it only when adjacent
codomain/domain endpoints match. Validation v7 causally identifies two-step
composition against an ablation that retains all direct inference. Arbitrary
morphisms, unbounded composition, and general category-theoretic cognition
remain unvalidated. Existing schema families remain similarity groups rather
than arrows in the comparison graph.

`EpisodeTrace` records the same scenes, transitions, hypotheses, experiment
questions, plans, decisions, and concept births used during inference. It also
records the complete deployed `MindConfig`, so a selected population descendant
cannot silently replay as the default agent. Replay, compression analysis, and
evaluation consume those records without a parallel agent implementation.

The Kaggle artifact is an overlay, not a fork. It contains the shared package,
the thin adapter, and a minimal agent registry. The notebook extracts those
files over the competition-provided official starter and invokes its `main.py`.

Development-only systems will depend inward on the symbolic package. The
symbolic package must never depend outward on an evolver, LLM, trace analyzer,
SQLite store, API server, or frontend. `tests/integration/test_kaggle_contract.py`
enforces the current inference closure.

The Kaggle closure contains symbolic values, perception, schemas, typed
structural credit, transformations and comparisons, reflecting abstraction,
causal and temporal hypotheses, planning, dependency graphs, mind, policy, and
trace types. Evaluation,
compression analysis, transforms,
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
Validation separately records wall time, peak traced Python allocation, and
canonical genome length. Experiment reports derive direction-aware
parent-relative improvements from persisted fitness rather than UI arithmetic.

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
