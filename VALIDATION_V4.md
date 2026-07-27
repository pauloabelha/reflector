# Reflector validation protocol v4

Status: confirmed on the untouched preregistered split.

V4 tests whether learned state-changing operations become executable
transformation objects whose compositions improve held-out control. It also
checks a finite typed comparison structure over those transformations. It does
not yet claim causal use of morphisms, general category-theoretic cognition,
or transfer to ARC-AGI-3.

## Identification strategy

The `transformation_composition` family has three phases.

1. A forced nine-action sequence supplies two clean observations of each
   cardinal translation. No policy can choose a different training action.
2. A forced demonstration establishes from level-advance evidence that the
   movable object's adjacency to the stationary object is an operative goal.
3. Eight unseen layouts require two primitive operations each. The balanced
   displacement set exercises right, left, down, up, and mixed-axis
   compositions; absolute positions and order vary by seed.

Every policy receives the same ten training actions and progress history.
Held-out layouts never recur, so exact frame tables cannot transfer. The oracle
requires 26 actions: ten forced training actions plus sixteen held-out actions.

## Policies

- `full`: default Kaggle-exportable `SymbolicPolicy`;
- `transformation`: the same inference package with unrelated concepts,
  reflecting abstraction, experiments, and accommodation disabled to isolate
  transformation planning;
- `no_transformations`: bit-identical to `transformation` except that learned
  transformation objects are unavailable;
- `score_only`, `context_table`, and `seeded_random` baselines.

The two causal variants are ordinary serialized `MindConfig` descendants and
use the same Kaggle-exportable inference code.

## Development and confirmation split

Development uses paired seeds 0–29. Confirmation uses seeds
90,000–90,029 and may be executed once only after the implementation, budget,
metrics, baselines, thresholds, tests, and protocol are committed.

The fixed action budget is 96. Paired confidence intervals use the existing
deterministic 2,000-resample bootstrap.

## Preregistered support criteria

All criteria must pass:

1. every action is legal;
2. all policies receive identical training actions and progress histories;
3. isolated transformation-policy completion is at least 0.95;
4. default full-policy completion is at least 0.95;
5. transformation efficiency exceeds the no-transformation ablation with a
   paired 95% bootstrap interval strictly above zero;
6. first-attempt intervention accuracy exceeds the same ablation under the
   same interval rule;
7. all four primitive transformation objects are constructed;
8. all four have represented inverse partners;
9. the finite comparison structure passes typed endpoints, identities, closed
   composition, and associativity;
10. at least one multi-step composed plan is operative per run.

Criterion 9 is a finite executable law check, not causal evidence that
morphisms improve control. Criterion 8 identifies inverse relations among
learned primitives; it does not yet show transfer from a forward operation to
an unobserved inverse.

## Development result

All criteria passed on seeds 0–29. Both the isolated transformation descendant
and the default full policy completed every run at the 26-action oracle
minimum. The no-transformation descendant never won. Transformation
composition improved paired first-attempt intervention accuracy by `0.84444`
(95% bootstrap CI `[0.75556, 0.92778]`); completed-run efficiency improved by
`1.0` because the ablation had no completed runs.

The report's embedded canonical payload SHA-256 is
`4c3b2377325fac256c831a7ddab6c9961883e0c5f935cc9c7b4575efcf915239`.
An immediate second run reproduced the JSON byte-for-byte.

## Untouched confirmation result

All ten criteria passed on the single execution of seeds 90,000–90,029 after
the protocol and implementation were frozen in commit `304ab0b`. Both the
isolated transformation descendant and the default full policy completed every
run at the 26-action oracle minimum. The no-transformation descendant never
won and averaged 23.70% completion within the 96-action budget.

Transformation composition improved paired first-attempt intervention
accuracy by `0.78333` (95% bootstrap CI `[0.68000, 0.88333]`). Completed-run
efficiency improved by `1.0` (CI `[1.0, 1.0]`) because the ablation completed
no run. All actions were legal, all policies received identical training
histories, all four primitive transformations and their represented inverse
partners were present, the finite typed comparison laws passed, and every
transformation run used multi-step plans.

The canonical report is `validation-v4-holdout.json`, with file SHA-256
`e9fb12623c7dc98c03250cdaa977d689be62a02c01938d6c24a47e34ffbd4c25`
and embedded result SHA-256
`e2ac8daa5b8ffa6f20d7f877c9cd75c9d2bb9fc6d25bfcf44f211b0bf8351235`.
No code or criterion changed after this result was viewed.

## Commands

Development:

```bash
.venv/bin/reflector validate --suite v4 --seed-start 0 --seeds 30 \
  --output validation-v4-development.json
```

Frozen confirmation:

```bash
.venv/bin/reflector validate --suite v4 --seed-start 90000 --seeds 30 \
  --output validation-v4-holdout.json
```
