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
reliability, symbolic description length, and deterministic replay rate. These
are initial operational approximations, not claims that epistemic compression
has already been solved.

Research descendants will additionally report completion and RHAE score, action
efficiency, resets, failed experiments, runtime, peak memory, planner
expansions, prediction accuracy, schema/concept description length, reuse,
duplicates, contradictions, orphans, replay savings, regression retention,
transformed-holdout performance, and improvement over their parent.

Required ablations are: no synthetic concepts, no counterfactual replay, no
schema-complexity pressure, no hierarchy pressure, score-only evolution, no LLM
mutation, and flat versus typed concepts. An abstraction is accepted only when
its measured benefit pays for its added complexity without breaking the Kaggle
gate.
