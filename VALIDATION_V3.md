# Reflector validation protocol v3

Status: frozen protocol executed once on the untouched confirmation split.

V3 tests the narrow claim that proposition-level contradiction can construct
an operative context condition that improves a later intervention. It does not
test psychological fidelity, general intelligence, or ARC-AGI-3 score.

## Identification strategy

The `constructive_accommodation` family has two phases.

During training, the environment exposes exactly one legal action on each
step. Every policy therefore executes the same eight actions and receives the
same level-progress history:

```text
actions:  1, 2, 1, 2, 1, 2, 1, 2
progress: 1, 1, 2, 2, 2, 3, 3, 4
```

In ordinary contexts, action 1 advances and action 2 does not. In perturbed
contexts containing a barrier-colored object, this relation reverses.
Absolute layouts and incidental movement effects differ on every transition.
Thus a complete-frame recurrence table cannot transfer, while grouping only
identical full transition signatures does not identify the common rule.

The confirmation phase presents eight never-seen layouts, half ordinary and
half perturbed in seed-dependent order. The oracle takes one action per
layout. The principal outcome is first-attempt intervention accuracy;
completion and action efficiency are secondary outcomes.

## Policies

- `full`: default Kaggle-exportable `SymbolicPolicy`;
- `constructive`: the same inference package with planning, ordinary
  reflecting abstraction, concepts, and active experiments disabled to
  isolate conditional accommodation;
- `fixed_ontology`: bit-identical to `constructive` except that constructed
  accommodations are unavailable to prediction and action selection;
- `score_only`: context-free empirical progress controller;
- `context_table`: exact visible-frame recurrence controller;
- `seeded_random`: deterministic seeded random policy.

`constructive` and `fixed_ontology` are serialized `MindConfig` descendants,
not benchmark-only policy implementations. Either can be exported through the
normal Kaggle path.

## Frozen development and confirmation split

Development uses paired seeds 0–29. Confirmation uses paired seeds
60,000–60,029 and may be executed once only after:

1. the implementation, policies, 40-action budget, metrics, thresholds, and
   bootstrap code are committed;
2. every unit and integration test passes;
3. Ruff and strict mypy pass;
4. the official local run, network-disabled Kaggle smoke test, and export pass;
5. the development report reproduces byte-for-byte.

## Preregistered support criteria

All criteria must pass:

1. every emitted action is legal;
2. all policies receive identical training action and scalar-progress
   histories within each seed;
3. isolated constructive-policy completion is exactly 1.0;
4. default full-policy completion is at least 0.95;
5. constructive efficiency exceeds fixed-ontology efficiency with a paired
   bootstrap 95% interval strictly above zero;
6. constructive first-attempt intervention accuracy exceeds fixed-ontology
   accuracy under the same interval rule;
7. the constructive policy has at least two evidenced operative conditional
   accommodations on average and constructs the specific held-out-relevant
   `color_present(5) -> action 2 adds level_advanced` condition in every run;
8. the fixed-ontology policy has no operative conditional accommodations.

The report is `supported` only when all eight criteria pass. It includes every
run and a SHA-256 digest of its canonical JSON.

## Development result

All criteria passed on seeds 0–29. Constructive accommodation improved paired
efficiency by `0.06749` (95% bootstrap CI `[0.05516, 0.08050]`) and
first-attempt intervention accuracy by `0.21250` (CI `[0.17500, 0.25000]`).
The report's canonical payload digest is
`da4e623d59112aed8085f6df8d86e8099b9b4eb2ba72d6253a968be3a40d6749`.
An immediate second run reproduced the JSON byte-for-byte.

## Commands

Development:

```bash
.venv/bin/reflector validate --suite v3 --seed-start 0 --seeds 30 \
  --output validation-v3-development.json
```

Frozen confirmation:

```bash
.venv/bin/reflector validate --suite v3 --seed-start 60000 --seeds 30 \
  --output validation-v3-holdout.json
```

## Untouched confirmation result

All criteria passed on seeds 60,000–60,029 without post-freeze changes.
Constructive accommodation improved paired efficiency by `0.06816` (95%
bootstrap CI `[0.05266, 0.08348]`) and first-attempt intervention accuracy by
`0.21250` (CI `[0.16667, 0.26250]`). Every policy received the same forced
training actions and progress history. Both the isolated constructive
descendant and the default full policy completed every run.

The canonical report is `validation-v3-holdout.json`, with embedded canonical
payload SHA-256
`4d9a1a164521dbd8670d94c745b8d9969b6e0661b22200f9285cbb3f4787d53b`.
No implementation, budget, baseline, threshold, or statistic was changed after
the confirmation report was viewed.
