# Reflector validation protocol v9

Status: protocol frozen; implementation and confirmation seeds have not been
executed.

V9 tests the narrow claim that a previously useful synthetic concept can be
retired when later intervention evidence makes it unreliable, removed from
future operative contexts without erasing its history, and reactivated when
new evidence restores its warrant. It does not test human forgetting,
psychological equilibration, optimal memory management, task-score
improvement, or ARC-AGI-3 generalization.

## Lifecycle contract

Retirement is reversible epistemic suppression, never deletion.

Each concept has:

- an immutable concept identity and definition;
- current support, opportunities, reliability, utility, and evidence;
- an explicit `active` or `retired` status;
- append-only activation, retirement, and reactivation events;
- the exact evidence counts and reason for every status transition.

Only active concepts may emit `synthetic_item` atoms into future schema
contexts or contribute children to newly constructed concept types. Historical
schemas, concepts, lifecycle events, and dependency edges remain inspectable.

The frozen default retirement rule is:

```text
opportunities >= 6
contradictions >= 3
empirical reliability < 0.35
```

The frozen reactivation rule is:

```text
current support >= support recorded at retirement + 2
empirical reliability >= 0.50
current counterfactual utility > 0
```

Repeated reflection over unchanged evidence may not emit another event.

## Identification strategy

For each seed, action ID, target event subject, layout atoms, incidental event
subjects, and ordering within each phase are generated deterministically.
Both causal variants receive the same `SchemaStore` after every transition:

- `concept_retirement`: ordinary `ConceptStore`;
- `no_concept_retirement`: identical configuration with only retirement
  disabled.

The phases are fixed:

1. **Admission:** three target effects establish the same active functional
   concept in both variants.
2. **Contradiction:** eight non-target effects for the same action reduce
   target reliability to `3/11`, below the frozen retirement boundary.
3. **Held-out use:** no new transition is learned. The enabled store must omit
   the target concept from `context_atoms`; the ablation must still emit it.
4. **Restoration:** six further target effects raise reliability to `9/17` and
   exceed retirement support by six. The enabled store must reactivate the
   same concept ID, not invent a replacement.

The main lifecycle uses a `level_advanced` target so the concept is an
`Activator[action=…]`. The scalar outcome itself does not trigger retirement
or reactivation; only the separately specified structural evidence thresholds
do.

## Independent controls

Three controls are required per seed:

1. **Noisy but viable:** three target and three non-target effects produce
   reliability `0.50`. The concept must remain active because contradiction
   alone is insufficient.
2. **Insufficient contradiction:** three target and two non-target effects
   remain below the opportunity and contradiction thresholds. The concept
   must remain active.
3. **Failed reactivation:** after retirement, only one new target effect is
   added. The concept must remain retired because support has not increased by
   two and reliability remains below `0.50`.

An independent validation-only oracle computes these outcomes directly from
the frozen inequalities and may not import lifecycle decisions from
`ConceptStore`.

## Provenance and non-interference

For every enabled run:

- lifecycle events must be ordered `activated → retired → reactivated`;
- all three events must name the same concept ID and definition;
- retirement must record the target support, opportunities, contradictions,
  reliability, utility, and evidence present at that moment;
- the reactivation event must point to the retirement event it supersedes;
- every lifecycle evidence ID must resolve to a schema in the same run;
- dependency-graph lifecycle edges must resolve;
- the retired concept and its historical schema dependencies must remain
  serialized;
- no held-out context atom may occur in lifecycle evidence;
- unrelated active concepts must keep the same status in enabled and ablated
  variants;
- repeated reflection without new schemas must be byte-idempotent.

## Split and execution discipline

Development uses seeds 0–29. Confirmation uses seeds
240,000–240,029.

The confirmation command may be executed once only after:

1. this protocol is committed;
2. lifecycle implementation, oracle, runner, causal ablation, controls,
   serialization, graph, UI, metrics, and tests are committed;
3. development seeds pass twice with byte-identical output;
4. the full Python suite, Ruff, mypy, frontend checks/build, offline Kaggle
   smoke, export, and prize audit pass;
5. the implementation/freeze commit and development hashes are recorded here
   without changing criteria or confirmation seeds.

The canonical command will be:

```bash
.venv/bin/reflector validate --suite v9 \
  --seed-start 240000 --seeds 30 \
  --output validation-v9-holdout.json
```

The report must embed a SHA-256 over canonical JSON before the hash field.

## Preregistered support criteria

All sixteen criteria must pass:

1. independent oracle predicts admission, retirement, and reactivation;
2. paired variants have identical evidence hashes at every phase;
3. both variants admit the same target concept ID;
4. enabled target concept retires after contradiction;
5. ablated target concept remains active after identical contradiction;
6. enabled held-out context omits the retired concept;
7. ablated held-out context retains the concept;
8. enabled target concept reactivates with the same identity;
9. lifecycle order is exactly activation, retirement, reactivation;
10. lifecycle evidence and dependency endpoints resolve;
11. retired knowledge and historical dependencies are never deleted;
12. noisy-but-viable control remains active;
13. insufficient-contradiction control remains active;
14. failed-reactivation control remains retired;
15. unrelated concept status is unchanged between variants;
16. repeated reflection is byte-idempotent.

Any failure yields `not_supported`. Passing supports only reversible,
evidence-driven concept retirement in this finite synthetic lifecycle.

## Claim boundary

The report must not describe retirement as forgetting, pruning optimality,
general equilibration, score improvement, or ARC transfer. It establishes only
that the shared symbolic package can revise the operative status of an
explicit concept under preregistered evidence while preserving an auditable
history.
