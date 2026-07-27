# Evaluation

The first gate is submission validity, not score:

- package imports without development dependencies;
- no network outside the official Kaggle gateway;
- legal action for every active observation;
- clean official environment advancement and termination;
- deterministic export from the same symbolic source;
- bounded runtime and memory.

The suite contains unit policy tests, object identity/event tests, schema and
concept evidence tests, deterministic trace round trips, metrics and comparison
tests, official adapter tests, an official `Swarm` integration run, exporter
closure tests, and a network-disabled packaged smoke test.

`reflector evaluate TRACE` currently reports actions, resets, transitions,
level advances, failed experiments, schema/concept counts, mean schema
reliability, causal/temporal hypothesis counts, planner expansions, symbolic
description length, schema-family/concept-type/language-operator counts,
abstraction description savings, recoverable redundancy, counterfactual replay
savings, action efficiency, pre-outcome prediction accuracy, schema/concept
reuse, duplicate/contradictory/dead/orphan structures, and deterministic replay
rate. Predictions are saved after one decision and scored only against the
following observed transition, preventing the current outcome from leaking
into its own prediction score. These are operational approximations, not claims
that epistemic compression has already been solved.

`reflector ablations TRACE` runs the same recorded observations through:

- full symbolic policy;
- no synthetic concepts;
- no counterfactual utility requirement;
- no schema-complexity charge;
- no explicit experiments;
- no planner;
- no hierarchy complexity pressure;
- flat concepts with reflecting abstraction disabled.

These trace-only ablations measure representational and policy divergence.
They do not replace environment reruns when measuring score or action savings.

`reflector population-evaluate` adds seeded color-permutation holdouts and
stores an immutable experiment manifest, candidates, detailed trace metrics,
and lineage in SQLite. The transform preserves the observation/action protocol
and recorded environment outcomes. It probes representational robustness; it
does not simulate counterfactual game dynamics and therefore cannot establish
RHAE improvement.

Candidates are ranked without collapsing all evidence into one scalar. The
current Pareto objectives maximize recorded level advances, deterministic
replay retention, schema reliability, and abstraction description savings,
and minimize planner expansions and schema description length. A candidate is
accepted into the archive only when no evaluated candidate dominates it on all
objectives. This is an experiment archive, not yet an automatic promotion to
the Kaggle default.

`reflector evolve` uses a deterministic proposal set by default. An explicitly
configured OpenAI-compatible provider may suggest the same constrained JSON
patches, but the response is untrusted input: unknown fields, nested values,
invalid types, and settings outside hard inference bounds are rejected. The
provider runs only in the development command. Candidate evaluation then runs
the deployed package in a fresh network-disabled process, twice, and rejects
nondeterminism. It records the slower of the two wall times, the larger Python
allocation peak reported by `tracemalloc`, and the canonical serialized genome
length. Runtime and allocation are machine-local diagnostics, not deterministic
fitness claims.

The local replay console is also an evaluation surface, not a source of new
metrics. It reconstructs every displayed policy snapshot from the trace,
renders recorded versus replayed decisions, and reads candidates and fitness
directly from SQLite. Its branch endpoint accepts only bounded `MindConfig`
patches and returns divergence over fixed observations with an explicit
non-rollout limitation.

Official environment reports add completion and RHAE score to the trace,
resource, structural, transformed-holdout, regression, and parent-improvement
metrics above. True counterfactual action savings still require restorable
environment branches.

`reflector evolution-ablations` compares the Pareto archive with score-only
selection and excludes descendants proposed by the optional LLM provider.
An abstraction is accepted only when its measured benefit pays for its added
complexity without breaking the Kaggle gate.

`reflector official-run` is the authoritative local score path. It invokes the
unchanged official `Swarm`/`Arcade` lifecycle and emits the toolkit scorecard
(including ARC/RHAE score and completed levels) beside Reflector's trace and
resource metrics. Trace replay never fabricates an official score.
