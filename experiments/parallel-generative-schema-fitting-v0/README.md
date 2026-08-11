# R2.1 — Parallel Generative Schema Fitting v0

This is a game-agnostic mechanistic experiment for the R2.1 substrate. It tests
whether one shared representation can keep reusable schema definitions,
competing partial bindings, explicit predicted shadows, compositional schema
invention, and temporal/interventional fitting distinct.

Run it with:

```bash
.venv/bin/python -m pytest -q experiments/parallel-generative-schema-fitting-v0/test_schema_engine.py
.venv/bin/python experiments/parallel-generative-schema-fitting-v0/run_mechanistic_experiment.py
```

The engine does not contain ARC roles, game names, action meanings, or semantic
labels. Observation adapters provide opaque typed support IDs and factual
relations; only their `evidence_id`s can increase schema/binding support.

## Current mechanistic coverage

1. Multiple overlapping bindings of one schema remain active.
2. Missing constraints project `Shadow` objects rather than facts.
3. Environment facts reify shadows; absence leaves them open.
4. Repeated relational motifs canonicalize to one content-addressed schema.
5. A promoted schema fits a novel partial case and predicts its missing
   relation.
6. A before/intervention/after schema works through the same partial-binding
   machinery.
7. Retrieval uses predicate/type indexes, so 1,000 irrelevant dormant schemas
   do not perturb the active frontier.
8. Existing partial bindings are extended rather than collapsed, and compatible
   bindings can propose an explicitly decomposable higher composition.

## R2.1 contract

R2.1 is the schema-first successor to the current R2 control loop. Its primary
state is a bounded active population of schemas, bindings, shadows and
explanations. Goal discovery, causal calibration and one-action control become
clients of this substrate; they are not its replacement.

The key R2.1 recursion is implemented: complete bindings advertise an output
type and become workspace atoms that may fill ports of higher schemas. Closure
is semi-naive, delta-triggered, indexed and bounded per epistemic cycle. There
is no fixed number of representational levels.
