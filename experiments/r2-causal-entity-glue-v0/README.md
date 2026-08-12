# R2 Causal Entity Glue v0

This focused experiment tests whether a locally correct atomic explanation can
still be causally under-scoped, and whether repeated settled transformation
coherence supports a smaller sufficient higher-order factorization.

Production ownership is `reflector2.r2.causal_entity`, upstream of role
grounding and `ProspectPlanner`. The planner receives supported spatial
bindings but contains no entity induction code.

Run:

```bash
PYTHONPATH=src .venv/bin/python experiments/r2-causal-entity-glue-v0/experiment.py
.venv/bin/python -m pytest -q tests/test_causal_entity.py
```

The AR25 arm is non-executing. It reads three content-addressed frames from one
append-only Arcade run and compares atomic versus lifted coverage on the same
two `ACTION_2` transitions. Visual adjacency and the game ID do not enter the
induction algorithm.

Status labels are used strictly: `IMPLEMENTED`, `OBSERVED`, `INFERRED`, and
`NOT DEMONSTRATED`.
