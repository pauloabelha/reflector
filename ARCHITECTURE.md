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

## Scheme category and compressed hierarchical options

The post-v82f inference core introduces a small finite-domain substrate in
`reflector/core/scheme_category.py`. It is intended to replace accumulation of
unrelated advisors with a common representation, not to add category-theory
terminology around game-specific routes.

A `FocusedRewriteObject` is a relational state object: it contains named
variables, their current values, finite goal domains, and one causally focused
variable. A grounded action displacement is a `TranslationMorphism`, an
endomorphism that changes only the focused variable while preserving the other
variables and all goal constraints. A `FocusMorphism` transfers causal focus
while preserving all relational content. Perception maps concrete frames into
these objects. Every observed intervention constructs a commuting square:

```text
concrete frame before ── action ──> concrete frame after
        │ abstraction                         │ abstraction
        ▼                                     ▼
relational object ─── predicted morphism ──> relational object
```

The action model gains authority only when the predicted and observed abstract
codomains are identical. A failed square is a typed causal contradiction and
quarantines the morphism. This is the operative naturality criterion: changing
layout, color names, or other nuisance presentation must not change the
relation between intervention and abstract effect.

`compile_focused_option` treats the variable's goal domain as a finite CSP and
performs bounded A* over confirmed morphisms. Its result is a hierarchical
option with:

- an initiation object;
- a primitive-action policy;
- a goal-domain termination condition;
- an exact expansion bound;
- raw and compiled description lengths;
- explicit compression utility.

An option may execute as a bounded exact plan without being inherited.
Retention requires positive minimum-description-length utility, and identical
option programs are stored only once while subsequent uses count as reuse.
This separates short-lived planning from durable knowledge compression and
prevents every successful trajectory from becoming another permanent policy
fragment.

The first binding is landmark-constrained shape embedding. Colored landmark
centers are Drescher-style synthetic items whose conjunction defines a latent
goal: every center must lie on one translation of the corresponding mover
mask. Perception may return several pixel-level embeddings. The CSP planner,
not a shape-specific tie-breaker, selects only embeddings reachable in the
intervention-grounded action lattice. The same representation covers plus, X,
diamond, clipped, translated, reflected, and color-renamed layouts.
Mover masks are completed under observed central symmetry before embedding,
so a pixel temporarily occluded by a crossing mover color does not mutate the
abstract object or its goal domain.
Once a morphism is causally confirmed, it also acts as a bounded belief-state
filter: the goal domains and non-focused variables persist through temporary
occlusion, while the focused variable updates only when its perceived center
matches the predicted displacement exactly. A focused-effect mismatch remains
a contradiction and quarantines the morphism.

When color ceases to identify an object, overlapping same-colored movers are
represented as a product object. One confirmed translation separates the
focused factor from the same-colored background by its removed/added pixels;
focus transfer exposes the next factor. Each normalized factor mask generates
a finite domain of reachable landmark subsets. A bounded exact-cover CSP
selects one placement per factor only when their covered landmark sets are
disjoint, exhaustive, and uniquely minimum-cost. The resulting factor routes
are compiled through the same focused-option planner.

Landmark and mover colors need not coincide. For clipped reference
constellations, large mover components and landmark groups form a bipartite
binding CSP. Central symmetry is completed outside the visible frame so a
boundary-clipped arm remains part of the latent mover mask. A binding is
compiled only when reachable subset embedding yields a unique minimum-cost
bijection. The complete multi-mover route is then one committed hierarchical
option, preserving mover identity through any intermediate recoloring.
Where visible swatches act as paint stations, the planner lifts position to
`(anchor, color)`. Shape–swatch intersection is a causal color transition.
Bounded A* must acquire the assigned landmark color and reach the embedding
target without later crossing a destructive swatch. This makes an intermediate
paint contact an explicit hierarchical subgoal rather than a rendering side
effect.

This implements a narrow Piagetian cycle:

1. assimilate a new layout into the existing focused-rewrite scheme;
2. predict the abstract consequence of an intervention;
3. preserve the scheme when the square commutes;
4. accommodate on disequilibrium by weakening the smallest false perceptual
   condition, such as replacing “four points form a plus” with “landmarks embed
   in a translated mover mask”;
5. retain the revision only when it compresses evidence and improves bounded
   planning.

The current scope is deliberately finite and symbolic. Arbitrary categories,
learned neural representations, unbounded program synthesis, and general
option discovery remain unproven. The target evidence and preservation gates
in `PLAN.md` determine whether this substrate becomes part of an accepted
agent.

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
