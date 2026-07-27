# Reflector validation protocol v2

V1 exposed two unvalidated mechanisms: cross-context abstraction and temporal
control. V2 tests those mechanisms directly without treating synthetic results
as an ARC score. An initial development run exposed that invariant controls
could be solved by the ordinary global causal planner, making the abstraction
comparison non-identifying. The development task was therefore revised to
require transfer conditional on a shared marker color. This final protocol and
all thresholds are frozen before the confirmation split is viewed.

## Suites and split

Development uses paired seeds 0–29. The untouched confirmation set is paired
seeds 30,000–30,029. Code, action budgets, baselines, thresholds, and bootstrap
logic must be frozen before the confirmation set is viewed.

The four interactive families are:

- `novel_context_transfer`: two marker colors select different controls over
  16 absolute layouts that never recur, requiring shared-context transfer
  rather than a global action average;
- `contextual_control`: four recurring layouts require different controls,
  detecting harmful over-generalization;
- `rare_object_click`: complex actions must remain grounded on the rare visual
  object;
- `procedure_transfer`: a three-action goal-reaching procedure recurs across
  eight novel absolute layouts, with a fourth distractor action.

The same eight policies and fixed budgets used by
`reflector_symbolic_diagnostics_v2` are evaluated on 30 paired seeds. The full
policy is the Kaggle-exportable `SymbolicPolicy`; no benchmark-only inference
adapter is allowed.

## Preregistered criteria

All of the following must pass for a `supported` result:

1. every emitted action is legal;
2. full-policy completion beats seeded random with a paired 95% bootstrap
   interval strictly above zero;
3. full-policy completion beats the score-only controller with the same
   interval rule;
4. full-policy efficiency beats the no-abstraction policy across the suite;
5. contextual completion is at least 0.75;
6. rare-object-click completion is at least 0.95;
7. procedure-transfer completion is at least 0.90;
8. full procedure efficiency beats no-planning with a paired 95% interval
   strictly above zero;
9. full novel-context efficiency beats no-abstraction with a paired 95%
   interval strictly above zero.

The full report must reproduce byte-for-byte. Official `bt11`, the packaged
network-isolated smoke test, and the complete test/type/lint suite must still
pass after the mechanism change.

Run development:

```bash
.venv/bin/reflector validate --suite v2 --seed-start 0 --seeds 30 \
  --output validation-v2-development.json
```

Only after freezing the implementation, run confirmation exactly once:

```bash
.venv/bin/reflector validate --suite v2 --seed-start 30000 --seeds 30 \
  --output validation-v2-holdout.json
```
