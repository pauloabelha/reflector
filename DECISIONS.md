# Decision log

## 2026-07-28 — Official public behavior outranks synthetic structure

The first complete 25-game official-API public run scored 0.0 with no level
completions, tying one official random-starter run. The agent formed many
schemas, concepts, and hypotheses, but no procedure or language operator
became operative. Therefore structure counts, compression, prediction
accuracy, and synthetic mechanism wins cannot qualify a descendant as the
current best agent without environment-level progress.

Future accepted descendants must first demonstrate reproducible official-game
improvement, then isolate the responsible mechanism with a same-environment
ablation. The full negative result remains in `PUBLIC_GAME_TEST_REPORT.md`.

## 2026-07-28 — Public recordings are evidence only if actions survive

The public run exposed an adapter defect: conversion from `FrameDataRaw` to
`FrameData` drops `action_input`, and the recorder serializes the default
`RESET` for every frame. Scorecard results remain valid, but those recordings
are not faithful gameplay replays. Public replay claims are suspended until
the conversion is fixed, regression-tested, and rerun.

## 2026-07-27 — Official starter is the repository root

Reflector was cloned directly from `arcprize/ARC-AGI-3-Agents`. The official
`Agent`, `Swarm`, and `main.py` lifecycle remains the execution shell.

## 2026-07-27 — One dependency-free policy core

All decisions live in `reflector.SymbolicPolicy`. Local and Kaggle adapters
translate protocol objects only. Generated notebooks embed the package; they do
not contain a separately maintained policy.

## 2026-07-27 — Inference closure is explicit

The Kaggle overlay uses an explicit inference-file allowlist. Optional LLM
agents retained from the starter are development-only and are no longer
imported by the core agent registry.

## 2026-07-27 — Offline compatibility is executable

`kaggle_smoke_test` uses a clean directory and Linux network namespace rather
than treating an environment flag as evidence that networking is disabled.

## 2026-07-27 — First symbolic language is constrained and empirical

The first DSL is composed of typed atoms, objects, events, scenes, transitions,
schemas, and synthetic concepts. Visual objects are same-color connected
components with greedy persistent identity matching. These are explicit
approximations. Concepts require repeated action-effect evidence and positive
utility after a description-complexity charge.

## 2026-07-27 — Counterfactual claims are bounded by observable evidence

Trace replay may credit description-length reduction, avoided rediscovery, and
repeated planner work. It must report zero action savings unless an actual
branch-and-replay environment run supplies the counterfactual outcomes.
Causal strength is an observed action/control rate difference with discounted
confidence, not a claim of complete causal identification.

## 2026-07-27 — The deployed configuration is the evolutionary genome

Population candidates are strict, bounded `MindConfig` values instantiated by
the same `SymbolicPolicy` shipped to Kaggle. Mutation providers return
untrusted structured patches; they cannot inject or replace policy code.
Candidate validation runs twice in a fresh network-disabled process before
SQLite persistence and Pareto comparison.

## 2026-07-27 — Transformed traces are robustness probes, not game rollouts

Seeded color permutations test representational retention while preserving
recorded outcomes. They do not model counterfactual environment dynamics and
cannot by themselves support claims about RHAE, action savings, or score
improvement.

## 2026-07-27 — The first web surface is local, evidence-backed, and offline

The Python analysis API reconstructs the same deployed policy from traces and
reads the same SQLite experiment records as the CLI. The strict TypeScript
frontend compiles to browser-native modules with no runtime framework, CDN,
remote font, telemetry, or separate data model. Recorded-observation branches
are labeled trace-only until an official environment snapshot mechanism can
generate genuine counterfactual outcomes.

## 2026-07-27 — Higher-order abstractions are evidence-bearing compilations

Schema families, concept types, and language operators are immutable symbolic
records with member evidence, raw and compiled description length, complexity,
and utility. The first language reflection recognizes repeated quarter-turn
predicates and adopts an orientation algebra only when at least three elements
and enough repeated support make the compiled representation shorter. This is
an operational approximation, not a claim of full Piagetian abstraction or
held-out transfer.

## 2026-07-27 — Predictions are scored before their outcomes are observed

Trace evaluation carries the event set predicted after one decision forward to
the next transition and scores set overlap only then. Structural diagnostics
count reuse, equivalent schemas, conflicting results, low-reliability schemas,
and concepts with missing evidence. Sandbox wall time and Python allocation
peaks are reported as machine-local diagnostics; deterministic operation and
description measures remain the stable comparison basis.

## 2026-07-27 — Accepted abstractions compile into future inference

Retained functional concepts become synthetic terms in later schema contexts,
accepted orientation vocabulary normalizes later rotation events, and reliable
schema families supply abstract effects and confidence to bounded planning.
This is the first operative reuse loop; it is not evidence of held-out transfer
or macro-action learning.

## 2026-07-27 — Target the code track and linked Paper Prize

The strongest current fit is a valid ARC-AGI-3 Kaggle code entry linked to the
Paper Prize. The symbolic thesis aligns with theory, novelty, universality, and
completeness, while current single-fixture evidence is not competitive-score
evidence. Selected `MindConfig` genomes now embed directly in the Kaggle
notebook. Reflector contributions are offered under MIT-0 or CC BY 4.0;
upstream starter code remains MIT. Account eligibility, public publication,
all-public-game evaluation, and a scored Kaggle rerun remain explicit manual
gates.

## 2026-07-27 — Predictions, value, exploration, and control stay separate

Reading Drescher's *Made-Up Minds* and Ramstad's MIT/LCS/TR-563 sharpened the
module boundary. Schemas estimate consequences and causal dependence; official
progress supplies goal value; sensory novelty supplies only epistemic pressure;
and the planner selects actions. Hidden global action fallback was removed so
disabling abstraction actually removes cross-context transfer. Repeated
successful trajectories can compile into evidence-bearing, MDL-positive
procedures, while negative current-context evidence gates global plans.

This controller is only a bounded approximation of Drescher's composite
actions, and Reflector's functional concepts are not yet his synthetic items.
Behavioral completion and efficiency ablations—not the presence of symbolic
structures—are the acceptance test. The source-to-contract mapping is recorded
in `references/SCHEMA_MECHANISM_NOTES.md`.

## 2026-07-27 — Compression does not define reflecting abstraction

Piaget's projection/reflection distinction adds a stricter acceptance boundary.
The six serialized layers are engineering strata, not developmental stages.
An MDL-positive structure becomes a reflecting-abstraction candidate only when
it derives from coordinated actions, projects them into a higher-order
representation, reorganizes them into a new operation, and has a measurable
effect such as transfer, composition, or reversibility.

Schema families and procedures have initial transfer evidence from validation
v2; the orientation algebra has structural composition evidence. Explicit
projection/reorganization records, inversion tests, abstraction-specific
negative evidence, and degradable erroneous abstractions remain future work.
Language nesting alone must not be described as reflected abstraction or
metareflection. See `references/REFLECTING_ABSTRACTION_NOTES.md`.

## 2026-07-27 — The next research gate is equilibration, not a larger macro

The authoritative online survey changes the next implementation priority.
Piaget's own equilibration account requires continuous interaction between
observables and coordinations, explicit use of negations, and structural
reorganization when a perturbation resists the current model. Inhelder and
Piaget distinguish temporal procedures from atemporal systems of
transformations. Campbell and Bickhard add the decisive warning that a control
hierarchy is not a knowing hierarchy.

Therefore Reflector will not claim higher-order reflection by adding deeper
procedures. The next benchmarked mechanism should instead record
contradictions and accommodation, distinguish procedures from operative
structures, support composition and reversal, test possible/impossible/
necessary reachability, and operate on learned structures as explicit inputs.
`VALIDATION_V3_DESIGN.md` records the proposed falsification suite before code
is written.

## 2026-07-27 — Compare transformations explicitly before claiming categories

Piaget's *Morphisms and Categories* supplies a concrete candidate for the
missing knowing-level object. Operatory transformations change contents;
morphisms compare contents or transformations; higher morphismic operations
compose the comparisons themselves. Reflector currently has transformations,
temporal procedures, and similarity-based families, but no typed mapping
between learned transformations.

The next representation should therefore distinguish a transformation system
from a comparison graph. A comparison must expose source, target, preserved
relations, and typed composition. Category-theoretic terminology is prohibited
until represented identities and composition pass closure, endpoint,
associativity, and identity tests. This follows Papert's own warning against
using the mathematics as superficial metaphor.

## 2026-07-27 — Reinforcement updates evidence structures, not one currency

The supplied Sutton and Barto PDF makes the boundary unusually explicit: the
book studies learning after state, action, and reward representations have
been selected, while calling construction of improved state representations
an unclear and open problem. It also treats cumulative scalar reward as the
formalization of all goals. This is a productive engineering reduction, not a
complete constructivist account.

Reflector therefore retains online interaction, pre-outcome prediction,
experimentation, models, planning, and bounded delayed credit, but records
external progress, proposition confirmation/contradiction, epistemic novelty,
and structural response as separate channels. A delayed structural trace names
the proposition and schema responsible; it is not a discounted scalar return.
The initial ledger is an evidence substrate only. Its `differentiate`,
`specialize`, and `integrate` records do not yet prove accommodation or alter
control. Those claims require the equal-return intervention and perturbation
ablations preregistered in `VALIDATION_V3_DESIGN.md`.

## 2026-07-27 — Accept conditional accommodation, not general equilibration

Validation v3 forced all policies through identical training actions and
scalar-progress histories, varied every absolute layout and barrier position,
and reserved seeds 60,000–60,029 until the code and criteria were committed.
On that untouched split, enabling conditional accommodation improved
first-attempt intervention accuracy over the otherwise identical fixed-ontology
descendant by 0.2125 (95% paired bootstrap CI [0.1667, 0.2625]) and efficiency
by 0.0682 (CI [0.0527, 0.0835]). All policies remained legal, and the default
full agent completed every run.

Conditional proposition amendments are therefore accepted into the operative
Kaggle inference path. The accepted claim is deliberately narrow: repeated
prediction contradiction can construct an evidenced shared context condition
that improves intervention in novel layouts. General equilibration,
psychological fidelity, arbitrary ontology invention, transformation reversal,
morphism composition, and official ARC generalization remain unvalidated.

## 2026-07-27 — Accept executable transformation composition, not categories

Validation v4 froze the implementation and criteria in commit `304ab0b`, then
ran seeds 90,000–90,029 once. All policies received identical forced primitive
and goal-demonstration histories. The isolated transformation descendant and
default policy solved every unseen layout at the 26-action oracle minimum;
the otherwise identical no-transformation descendant never won.
First-attempt intervention accuracy improved by 0.7833 (95% paired bootstrap
CI [0.6800, 0.8833]) and efficiency by 1.0 (CI [1.0, 1.0]).

Learned translation objects and their bounded composition are therefore
accepted into the operative Kaggle path. The separate typed comparison graph
passes finite endpoint, identity, closure, and associativity checks, and all
four learned primitives have observed inverse partners. These are structural
facts, not causal evidence for morphisms or transfer to an unobserved inverse.
Modal reachability has finite unit coverage but no held-out causal validation.
Category-theoretic cognition and official ARC generalization remain
unvalidated.

## 2026-07-27 — Accept bounded modal control, not general modal logic

Validation v5 froze its revised task and implementation in commit `6ecec4f`,
then ran seeds 120,000–120,029 once. Long-but-possible and impossible goals
both exceeded the ordinary planner horizon, eliminating short-plan failure as
an implicit modal side channel. The isolated modal descendant solved all runs
at the 26-action oracle; disabling only modal access reduced win rate to
33.33%. First-attempt accuracy improved by 0.5014 (95% paired bootstrap CI
[0.4597, 0.5497]) and efficiency by 0.7281 (CI [0.5878, 0.8638]).

Exhaustive finite possible/impossible reachability is therefore accepted into
the operative Kaggle path. Impossibility requires explicit perceived bounds
and frontier exhaustion; exceeding the expansion budget returns `unknown`.
The claim excludes necessity, arbitrary obstacles, general modal logic,
unobserved inverse construction, causal morphism use, and official ARC
generalization.

## 2026-07-27 — A generated comparison graph is not transfer evidence

The current finite comparison graph constructs all pairwise parameter deltas,
so its law checks cannot identify a learned or causally useful morphism.
Validation v6 must first introduce context-typed transformation systems and
infer a preserved map from multiple observed operator correspondences. Its
held-out effect must be absent from ordinary schemas and recoverable only by
applying that evidenced map. A same-information ablation, leakage audit, and
negative-control world are mandatory. The design and its rejection conditions
are recorded in `VALIDATION_V6_DESIGN.md` before implementation.

## 2026-07-27 — Accept direct causal comparison transfer, not composition

Validation v6 froze its context-typed operator mechanism, independent oracle,
leakage checks, negative control, and thresholds in commit `66ce650`, then ran
seeds 150,000–150,029 once. The isolated and default descendants completed
every run at the 32-action oracle. Disabling only application of learned
comparisons removed every inferred withheld operator, produced zero wins, and
reduced mean completion to 55%. First-intervention accuracy improved by 0.6851
(95% paired bootstrap CI [0.5902, 0.7888]) and efficiency by 1.0 (CI
[1.0, 1.0]).

Direct transfer through a uniquely identified finite system comparison is
therefore accepted into the operative Kaggle path. Each inferred operator
names its perceived domain, source operator, typed comparison, and calibration
evidence; inconsistent mappings are rejected. This does not validate
composition of comparisons, arbitrary morphisms, general category theory, or
official ARC generalization.

## 2026-07-27 — Accept bounded comparison composition, not general categories

Validation v7 froze its `A → B → C` topology, perceived link tokens,
independent oracle, leakage checks, and composition-only ablation in commit
`004e509`, then ran seeds 180,000–180,029 once. The isolated and default
descendants completed every run at the 96-action oracle. The ablation retained
both direct maps and direct inferred operators but averaged 74.72% completion.
First-intervention accuracy improved by 0.6365 (95% paired bootstrap CI
[0.5927, 0.6797]) and efficiency by 0.6901 (CI [0.5401, 0.8200]).

Endpoint-valid comparison composition through an inferred intermediate
operator is therefore accepted into the Kaggle inference path with a fixed
three-hop bound and ordered provenance. This is evidence for one finite
two-step synthetic family, not arbitrary morphisms, unrestricted category
theory, or official ARC generalization.

## 2026-07-27 — Represent language invention, but do not claim general invention

Recording an accepted operator and a language-version label does not establish
reflection over the mechanism that invented it. The cyclic-predicate inducer
is therefore promoted to a serializable, parented structure. It emits explicit
accepted or rejected proposals, pays a separate complexity cost, records the
evidence and products that revise it, and appears in the dependency graph and
replay UI. Accepted operators preserve immutable provenance to the mechanism
revision that proposed them.

The same-schema ablation disables this mechanism and produces neither proposals
nor an orientation operator. A repeated-evidence test also distinguishes a
provisional mechanism from one whose product utility pays the mechanism-level
complexity charge. The accepted claim is limited to explicit meta-evaluation of
one bounded, hand-authored invention strategy. It is not autonomous discovery
of arbitrary DSLs, source-code evolution, or official ARC generalization.

## 2026-07-27 — Accept bounded language-mechanism reflection, not general invention

Validation v8 froze its independent utility oracle, same-evidence ablation,
weak and non-cyclic controls, held-out intervention, provenance checks, and
fourteen criteria in commit `51997a4`. The single untouched run over seeds
210,000–210,029 passed every criterion. All enabled histories constructed one
operator and one positive-utility validated mechanism revision; all ablations
and controls abstained as required.

Explicit meta-evaluation of the cyclic-predicate inducer is therefore accepted
as a bounded mechanism result. The effect is a held-out representational
normalization, not improved game score or action efficiency. General language
invention, autonomous source changes, psychological metareflection, and
official ARC transfer remain unvalidated.
