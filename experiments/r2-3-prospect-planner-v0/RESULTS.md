# R2.3 ProspectPlanner v0 results

## Conclusion

The engineering hypothesis is supported, but the gameplay hypothesis is not
demonstrated. R2 can represent an evidence-bounded `GoalContract`, derive a
deterministic `GoalProspect`, and authorize only the first command of a
supported terminal-reaching factorization without turning simulation into
evidence. Synthetic tests show the intended temporary-regression capability.
The recorded AR25 prefix produced no planner divergence, however, and the
available multi-game archives were not rich enough to identify a legitimate
candidate fork.

## IMPLEMENTED

### 1. Repository understanding

The authority path is R2 semantic proposal -> R2 grounding and empirical
effect table -> controller-neutral `ControlProblem` -> planner hypothetical
search -> R2 validation of the returned exact first command -> one environment
action -> R2 settlement. The planner owns neither observations nor evidence.
The pre-change audit is recorded in
[`docs/R2_3_PROSPECT_PLANNER_UNDERSTANDING.md`](../../docs/R2_3_PROSPECT_PLANNER_UNDERSTANDING.md).

### 2. Exact GoalContract representation

R2 owns a frozen `GoalContract` with:

- stable contract ID and protocol;
- environment terminal (`level_completion`, `game_completion`, or
  `score_increase`);
- candidate contributor verb, observable, relation, and numeric target;
- status `OPEN`, `SUPPORTED`, or `REFUTED`;
- environment evidence references, semantic provenance, and an explicit
  countercondition.

Semantic proposals always compile as `OPEN`; citations are provenance, not
empirical support. Only environment-cited adjudication can support or refute
the contract. The planner receives a frozen `GoalContractBasis` projection.

### 3. Exact GoalProspect semantics

`GoalProspect` is a derived, explicitly non-evidential summary of bounded
search. It records terminal status, best supported depth, retained
terminal-reaching factorization count, weakest edge support and confidence,
unresolved preconditions, protected invariants, identity risk, expected local
verb orientation, search budgets, and option-preserving first-command count.
No field increases causal support.

### 4. Search and dominance rules

`ProspectPlanner` searches only command-scoped effects meeting the configured
support and confidence thresholds. Depth, expansions, frontier, milestones,
and retained goal factorizations have hard limits. Terminal paths are ordered
deterministically by contract relevance, weakest-link support, weakest-link
confidence, lower risk, shorter depth, option preservation, local orientation,
and stable command IDs. A locally adverse first command is eligible only when
an explicit supported path reaches the contributor terminal. The certificate
is `FIRST_COMMAND_ONLY`; settlement invalidates the continuation and forces
replanning. With no active contract, the backend preserves the existing
bounded local-milestone behavior.

### 5. Tests added

Eight focused ProspectPlanner tests cover GoalContract evidence authority,
temporary regression, rejection of false regression, strong-long versus
weak-short paths, no-contract compatibility, byte determinism and hard
budgets, nuisance invariance, and end-to-end R2 adapter/certificate behavior.
Arcade presentation tests cover the backend selector and visible
`PLANNER · GOAL PROSPECT` panel. The experiment has two artifact-contract
tests.

## OBSERVED

### 6. Test results

- Focused planner/R2/Arcade/experiment set: **33 passed**.
- Canonical suite excluding the separately tracked score-document integrity
  test: **187 passed**.
- `py_compile` and `git diff --check`: passed.

The two score-document integrity tests fail because their required
`parallel-cognitive-workspace-v1-16/artifacts/SUMMARY.json` and 25
`online-registry-development/*/RESULT.json` inputs are absent. Those files are
part of broad user-owned experiment deletions that predated R2.3 work and were
left untouched.

### 7. AR25 divergence scan

The non-executing scan replayed the documented action-17 prefix to reconstruct
evidence at 17 decision boundaries. One-step R2, bounded best-first, and
ProspectPlanner ranked the same observer state at each boundary. The empirical
effect-table digest was unchanged by all rankings.

- Boundaries scanned: **17**.
- Prospect plans found: **2**, at boundaries 13 and 14.
- Selected action at both: `ACTION_3`.
- Plan depths: **4** and **3**.
- Immediate orientations: both **preferred**.
- Divergences: **0**.
- Locally adverse Prospect divergences: **0**.
- Candidate actions executed by the scan: **0**.

### 8. Multi-game candidate scan

Only 11 tracked context-spinoff checkpoints remained available: ar25, cd82,
cn04, ft09, ka59, sb26, sc25, sp80, su15, tu93, and wa30. None contained the
frozen R2.2 grounded explanation, exact command-scoped effect table, and
GoalContract required by the preregistration. Therefore **0 of 11** were
eligible. This is not a completed scan of the requested 25-game corpus; the
remaining serialized state was unavailable, and no candidate was fabricated.

### 9. Exact matched forks executed

**Zero.** The protocol authorized a matched A/B/C environment fork only after
freezing an eligible divergence. Neither scan produced one.

### 10. Every causal first-action divergence

**None observed.** All 17 AR25 first actions matched, and the archive inventory
yielded no executable candidate.

### 11. Immediate potential change for each divergence

Not applicable because there were no divergences. The two AR25 Prospect plans
that matched the other arms predicted preferred local changes, not temporary
regressions.

### 12. Prospect change that justified each divergence

Not applicable. At the two plan-bearing AR25 boundaries the reported change
was `terminal-depth-decreased`, but it did not change the selected first
action.

### 13. Real environment settlement

No candidate fork was executed, so there was no real environment settlement
of a Prospect-specific divergence and no real support added to a GoalContract.

### 14. Score/progress consequence

None measured. The scan did not execute candidate actions and therefore cannot
claim a level, score, or progress improvement.

### 15. Runtime cost

Across the 17 sequential AR25 ranking calls:

| Arm | Total | Mean/boundary | Maximum |
|---|---:|---:|---:|
| one-step | 3231.040 ms | 190.061 ms | 255.963 ms |
| bounded best-first | 1058.160 ms | 62.245 ms | 128.162 ms |
| ProspectPlanner | 1064.195 ms | 62.600 ms | 127.164 ms |

These are complete R2 ranking timings from a sequential replay, not an isolated
backend microbenchmark. Cache warming and shared grounding make cross-arm
comparisons descriptive only. In this scan ProspectPlanner added 0.355 ms to
the mean bounded-arm decision time.

## INFERRED

The implementation is capable of selecting a locally adverse first step when
and only when a supported terminal factorization requires it: the controlled
synthetic world selects the adverse `B -> C` route over a locally improving
dead end, while the false-regression control selects the direct improving
route. This establishes mechanism capability under the test model, not
real-game usefulness.

## NOT DEMONSTRATED

### 16. Strongest negative result

The strongest negative result is the absence of any real causal first-action
divergence. Even when ProspectPlanner found supported AR25 terminal routes, its
first command matched one-step and bounded planning. The available multi-game
artifacts could not test the hypothesis at all because they lacked the frozen
causal and contract state.

### 17. What remains missing

R2.3 has not demonstrated a useful temporary regression, a GoalContract
supported by a live level transition, improved level completion, a score gain,
or cross-game generality. The current archives also do not provide a complete
25-game candidate corpus. A live terminal observation needs explicit
environment-terminal citation before the contract can become `SUPPORTED`;
ordinary success elsewhere is deliberately insufficient.

### 18. Recommended next experiment

Instrument the next prospective breadth run to persist a frozen
`ControlProblem`, command-scoped effect table, OPEN GoalContract, and all three
rankings at every decision boundary. Before any intervention, preregister and
freeze the first eligible locally adverse divergence, then execute a matched
one-step/bounded/Prospect fork from the identical saved environment state.
Measure immediate potential, successor prospect, contract settlement, level
progress, score consequence, and wall time. Do not tune on the AR25 prefix.

## Artifacts

- [`ar25-prefix-scan.json`](artifacts/ar25-prefix-scan.json)
- [`multi-game-candidate-scan.json`](artifacts/multi-game-candidate-scan.json)
- [`summary.json`](artifacts/summary.json)
