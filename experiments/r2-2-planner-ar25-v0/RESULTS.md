# R2.2 planner AR25 v0 results

## Conclusion

The engineering hypothesis is supported: R2 can compose supported causal
shadows to depth 3--4, authorize exactly one action, settle that action, erase
the continuation, replan, and safely hand repeated confirmed positive edges to
the existing fast path. The control-improvement hypothesis is **not** supported
by these forks. Deterministic planning matched original R2 exactly. Qwen caused
one real first-action divergence, but it was slower and worse on immediate
environment-grounded progress and did not change score.

## IMPLEMENTED

- `src/reflector2/planner` is a controller-independent package. It imports no
  R2 modules. `ControlProblem` supplies transition, measurement, invariant, and
  state-key callbacks; `PlannerBackend` is the injection contract.
- `NoPlanPlanner` delegates to the host's original one-step controller.
  `BoundedBestFirstPlanner` performs deterministic bounded causal composition.
  `ModelPlanner` accepts a `PlanningModel`, then deterministically validates
  every proposed edge before returning a plan.
- `QwenPlanningModel` and `LunaPlanningModel` implement the same structured
  model contract. R2 wiring supports its existing provider-neutral HTTP poster
  and a local Qwen GGUF process transport. No model output directly authorizes
  an action.
- Generic milestone shadows are derived from the active explanation:
  terminal completion, active residual reaching zero, and preferred residual
  change. They are explicitly prospective and bounded to four.
- Search composes only effects above explicit support/confidence thresholds,
  rejects out-of-frame/static-collision successors, preserves role topology,
  and ranks terminal milestone, useful milestone, preferred progress,
  confidence/risk, path length, then deterministic command identity.
- A plan certificate records the explanation, potential, milestone, causal
  composition, search budgets, first exact command, predicted successor,
  protected invariants, and invalidation conditions. It grants
  `first-command-only`; continuation authority is always absent.
- Every environment successor invalidates the prospective continuation. A
  confirmed positive plan edge may separately contribute to the old bounded
  fast path only after settlement; its certificate and route are stripped.
  Negative planned edges cannot earn fast-path authority.

## Exact control-factorization semantics

For one grounded explanation and actor/target role binding, the adapter takes a
read-only snapshot of supported command-scoped actor/target translations. A
backend searches or proposes a sequence

```text
observed S0 --supported effect--> hypothetical S1 ... --> milestone shadow
```

Every hypothetical successor remains outside empirical support. R2 promotes
only the first command to `PLAN_ELIGIBLE`, commits that exact `ActionCommand`
through the existing runtime boundary, settles identity/mechanism/potential
from the real successor, invalidates the whole certificate, and ranks again.
If no validated composition reaches a milestone, normal one-step
`PROBE_ELIGIBLE`/`PROGRESS_ELIGIBLE` control remains authoritative.

## OBSERVED

### Reproducibility

- Branch: `planner`
- Base commit: `3ae4e3666819135b7fdb88faf0204dab6f0a5f00`
- Tested worktree diff SHA-256:
  `586a566085727f6f688c1444af665602532b34cfe00aff9aa66b96f1e1901c0b`
- Environment build: `environment_files/ar25/0c556536`
- Stored trace reference: the `R2_1.md` replicated action-17 clear,
  `ACTION_1, ACTION_2 x 11, ACTION_3 x 5`
- Primary artifacts: `artifacts/matched-result-v4.json` and
  `artifacts/matched-additional-v4.json`
- Qwen model: `Qwen3VL-4B-Thinking-Q4_K_M.gguf`, 2,497,281,472 bytes,
  SHA-256 `474ecaf1284aa6ff3273fb796c3cba55d2ee33ec0d8c63464fbd84500a9a462d`
- Qwen runtime: CPU `llama-cli` version 8660 (`d00685831`)
- Supplemental model-wiring SHA-256:
  `01917a5fa4688af5613cc9cccae1a85ef4d4aee992a2f3e2f65b6182b8084d5f`

Exact commands:

```bash
PYTHONPATH=src .venv/bin/pytest -q --ignore=tests/test_scores_doc.py

PYTHONPATH=src .venv/bin/python -u \
  experiments/r2-2-planner-ar25-v0/experiment.py \
  --boundaries 12 --suffix-budget 6 \
  --output experiments/r2-2-planner-ar25-v0/artifacts/matched-result-v4.json

PYTHONPATH=src .venv/bin/python -u \
  experiments/r2-2-planner-ar25-v0/experiment.py \
  --boundaries 13 14 --suffix-budget 6 --without-model \
  --output experiments/r2-2-planner-ar25-v0/artifacts/matched-additional-v4.json
```

Hard planner budgets were depth 8, frontier 64, expansions 256, milestones 4,
minimum effect support 1, and minimum confidence 0.6. Each arm independently
replayed the exact prefix into a fresh offline environment/observer. Before
suffix control, the runner asserted equal frame, effect-table, and pre-planner
explanation/role-grounding digests.

### Deterministic original-vs-factorization result

| Fork | State digest | Original suffix | Deterministic suffix | Completion | Plan depths / expansions |
|---|---|---|---|---|---|
| 12 | `4df3dea7...17eb` | `3,3,3,4,3,3` | `3,3,3,4,3,3` | neither within 6 | `4/50, 3/45, 3/45` |
| 13 | `5a68afdf...851e` | `3,3,4,3,3,3` | same | both action 19 | `4/50, 3/45, 3/45` |
| 14 | `d61a7a52...fe0a` | `3,4,3,3,3` | same | both action 19 | `3/45, 3/45` |

Across the three forks, deterministic planning was invoked 12 times, found 8
plans, returned no-plan 4 times, and expanded 370 nodes for successful plans.
All 8 planned first steps were confirmed by environment settlement; there were
zero first-step refutations. The two arms each spent 4 actions probing, 13 on
predicted progress, had 3 identity failures, 0 mechanism failures, and 5
fast-path interactions. Both completed 2/3 fork rollouts. There were zero
action divergences and zero score divergences.

No terminal milestone was directly confirmed inside a certificate: depth-N
certificates correctly remained `PENDING_REPLAN` after their first confirmed
edge. Subsequent certificates re-established the factorization from observed
state; they did not reuse a cached route.

### Model-validated Qwen result

Qwen was tested at boundary 12 with the same frame, causal-effect table, active
explanation basis, and six-action suffix budget. It was invoked 6 times,
produced 3 accepted depth-3 factorizations and 3 validated no-plan outcomes.
All 3 authorized first steps settled as confirmed. It expanded/validated 3
edges per accepted plan, had zero identity/mechanism failures, and did not
complete the level. Total planner wall time was 262.0 seconds versus 0.89
seconds for deterministic planning and 0.82 seconds for fallback ranking.

Concrete divergence:

```text
predecessor state: 5a68afdfbbc1999353a1f842c7d96bfa694f8aa9bc1c6e2c474b3d407153851e
original R2:       action 3, actual preferred progress +3
Qwen ModelPlanner: action 1, actual preferred progress -1
settlement:        Qwen's causal first-step prediction confirmed
score effect:      none; neither arm completed within this suffix
```

The later Qwen trajectory was `3,1,3,1,2,1`, versus original
`3,3,3,4,3,3`. Only the first divergence is causally matched; after it, states
differ and later choices are trajectory observations, not matched
counterfactuals.

### Tests

The final suite passed 177 tests when excluding `tests/test_scores_doc.py`.
Focused planner/experiment tests cover:

- hypothetical-state/evidence separation and unchanged support;
- arbitrary-depth exact-one-action certificates;
- invalidation on mismatch, identity break, mechanism failure, and unexpected
  successor;
- no cached plan route in fast-path state;
- fresh fast-path authorization from repeated settled positive plan edges;
- deterministic, translated, recolored, reoriented, and scaled scenes;
- hard depth/frontier/expansion budgets;
- injectable alternate planner backend and reset persistence;
- original/factorization backend swapping;
- Qwen/Luna structured adapters, local CLI argv isolation, malformed output,
  unsupported command, invariant, milestone, and budget rejection;
- matched-state/effect/explanation assertions and action-vs-abstention audit.

The unexcluded full suite still has two known artifact-document failures caused
by user-owned deleted historical result files; no planner test failed.

## INFERRED

- Deterministic R2.2 has useful calibrated foresight: depth-3/4 compositions
  repeatedly predicted real first successors without adding empirical support.
  This is stronger than a pretty internal route but weaker than improved
  control because its first actions were identical to original R2.
- The model boundary is genuinely model-agnostic at the contract level. Qwen
  was live-tested; Luna used the same request, transport normalization, and
  validator in contract tests, but was not live-called because no Luna/OpenAI
  credential was configured.
- The Qwen divergence shows that a pluggable model can alter control through
  validated causal composition. This particular divergence is evidence of
  different foresight, not better foresight.

## NOT DEMONSTRATED

- No planner beat original R2 on AR25 level 1.
- No deterministic planner action divergence or action-efficiency improvement.
- No useful model divergence or environment-score improvement.
- No directly observed milestone confirmation in these bounded suffixes.
- No cross-game or cross-level generalization.
- No basis yet for promoting repeated compositions into a `SkillSchema`.

## Failure analysis

The deterministic backend's available supported translation dynamics made the
same first action optimal as one-step R2 at every matched state. Around contact,
both encountered the same identity failure; the planner correctly refused to
invent merge/split dynamics. An intermediate implementation also exposed a
fast-path integration regression: plan edges could not build settled policy
support, causing abstention before the original clear. The final code repairs
that without retaining plan continuation, and v4 shows identical action-19
clears.

Qwen found different depth-3 compositions, but the first matched deviation
temporarily worsened the active potential. Its model calls were roughly 300x
the deterministic planning cost and did not produce a score benefit. More
tokens or weaker validation would not be justified by this evidence.

## Single next experiment

Run a **non-executing divergence scan over every committed prefix in all three
repaired AR25 clear traces**, using frozen evidence and explanation digests.
Select the first state where deterministic factorization proposes a different
first command (preferably a temporarily non-greedy command) from original R2,
then run exactly one matched real A/B fork from that state. If the scan finds
no such state, report that the existing AR25 trace family contains no testable
deterministic-planner intervention and move to a game with two supported action
directions; do not tune AR25 or weaken the gates.
