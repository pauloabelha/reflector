# Decision log

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
