# R2.2 planner AR25 v0

This is a same-knowledge control experiment, not an AR25 solver. It replays a
committed prefix independently into three offline ARC environments and three
fresh R2 observers. All arms receive the same action-free FIT proposal, observations,
role grounding, learned causal effects, action budget, and environment state.
The runner asserts exact digests for the fork frame, causal-effect table, and
pre-planner explanation/role-grounding basis before comparing actions.

- Arm A injects `NoPlanPlanner`, which cleanly delegates to the frozen current
  one-step `FrameSchemaObserver.rank_actions()` policy.
- Arm B injects `BoundedBestFirstPlanner`, which may select the first command
  of a bounded supported `ControlFactorization`.
- Arm C injects `ModelPlanner(QwenPlanningModel(...))`. Qwen proposes only
  command IDs; the same generic simulator rejects any unsupported,
  inapplicable, invariant-breaking, over-budget, or milestone-free proposal.

Arms A/B remain the primary same-knowledge causal comparison. Arm C is an
exploratory same-input model-planner comparison because a pretrained model is
an additional reasoning source. Prefix evidence acquisition is fallback-only
in all three arms; each experimental backend is installed only at the fork.

The default audit uses the documented action-12 pivot and the next two exact
successful-prefix boundaries. Prefix actions calibrate both arms and are not
selected by either experimental controller. Every suffix action is selected,
executed once, settled from the environment successor, and replanned. If R2
does not authorize a command, the arm stops instead of executing an advisory
ranking.

Run from the repository root:

```bash
PYTHONPATH=src .venv/bin/python experiments/r2-2-planner-ar25-v0/experiment.py \
  --boundaries 12 --suffix-budget 6 \
  --output experiments/r2-2-planner-ar25-v0/artifacts/matched-result-v4.json

PYTHONPATH=src .venv/bin/python experiments/r2-2-planner-ar25-v0/experiment.py \
  --boundaries 13 14 --suffix-budget 6 --without-model \
  --output experiments/r2-2-planner-ar25-v0/artifacts/matched-additional-v4.json
```

AR25 names, action prefixes, and fixture semantics occur only in this
experiment. Production planner code contains no game identity, route, action
meaning, palette, or coordinate rule.

The planner itself lives at `src/reflector2/planner`, outside the R2 package.
R2 is an adapter client and receives a `PlannerBackend` by dependency
injection; see the package README for the interchange contract.
