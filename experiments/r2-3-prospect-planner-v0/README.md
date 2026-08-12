# R2.3 ProspectPlanner v0

This experiment evaluates goal-respecting causal factorization without granting
hypothetical states empirical authority.

The AR25 scan replays only the already documented action-17 prefix to
reconstruct the exact evidence available at each boundary. At every boundary it
then performs three non-executing rankings over the same observer state:

- A: `NoPlanPlanner` (one-step R2);
- B: `BoundedBestFirstPlanner`;
- C: `ProspectPlanner` with the same grounded FIT proposal plus one OPEN
  `FIT-terminal -> level_completion` GoalContract.

No candidate action from the scan is sent to ARC. Effect support is hashed
before and after all three rankings and must remain unchanged.

The multi-game inventory is fail-closed. Archived material is eligible only if
it exposes enough state to establish two supported causal alternatives, an
active grounded verb/explanation, and an evidence-bounded GoalContract. Older
artifacts cannot be upgraded by inference merely because R2.3 now defines the
missing object.

Run:

```bash
PYTHONPATH=src .venv/bin/python \
  experiments/r2-3-prospect-planner-v0/experiment.py
```

The command writes JSON artifacts under `artifacts/`. A matched environmental
fork is authorized only after the scan freezes an eligible divergence.
