# Reflector validation protocol v5

Status: confirmed on the untouched preregistered split.

V5 tests whether an exhaustive finite reachability judgment over learned
transformations improves held-out control. It does not test general modal
logic, necessity, obstacle reasoning, unobserved inverse transfer, morphism
causality, or ARC-AGI-3 performance.

## Identification strategy

The `modal_reachability` family has three forced training phases.

1. Four actions supply two clean observations of right and down translations.
2. A forced right action demonstrates that adjacency between the persistent
   movable object and stationary target advances a level.
3. A forced response action demonstrates the appropriate response to one
   state proven unreachable by exhaustively exploring the represented finite
   board under the learned operators.

The eight held-out layouts contain four possible and four impossible adjacency
goals in randomized order and positions. Every possible goal requires four
primitive actions, exceeding the ordinary transformation planner's fixed
depth of three. Consequently, both a long-but-possible state and an impossible
state produce no ordinary short plan. The modal descendant exhausts the finite
state graph: it selects the first action of a shortest path for a possible
goal, or the evidence-grounded response only after the reachable set is
exhausted.

All policies receive the same six training actions and scalar progress
history. Absolute held-out layouts do not recur. The oracle requires 26
actions: six forced training actions, sixteen movements over possible
layouts, and four impossibility responses.

## Causal comparison

- `full`: default Kaggle-exportable `SymbolicPolicy`;
- `modal`: the same inference package with unrelated concepts, experiments,
  accommodation, and reflecting abstraction disabled;
- `no_modal`: bit-identical to `modal` except that finite modal classification
  and its response are unavailable;
- `score_only`, `context_table`, and `seeded_random` baselines.

The ablation retains the same perception, schemas, learned transformations,
goal evidence, ordinary depth-three transformation planner, legal actions,
training demonstrations, and external progress. It removes only access to the
exhaustive reachability result. Both causal variants are serializable
`MindConfig` descendants exported without policy translation.

## Development revision

The initial development task used possible goals within the ordinary planner
horizon. It was rejected: both causal variants solved at the oracle because
ordinary plan failure plus the globally successful response schema served as
an implicit reachability side channel. No confirmation seeds had been defined
or viewed. The task was revised so long possible and impossible states both
lack a short plan; only exhaustive reachability distinguishes them.

## Development and confirmation split

Development uses paired seeds 0–29. Confirmation uses seeds
120,000–120,029 and may be executed once only after implementation, action
budget, metrics, baselines, thresholds, tests, and this protocol are committed.

The fixed action budget is 72. Paired confidence intervals use the existing
deterministic 2,000-resample bootstrap.

## Preregistered support criteria

All criteria must pass:

1. every action is legal;
2. all policies receive identical training actions and progress histories;
3. isolated modal-policy completion is at least 0.95;
4. default full-policy completion is at least 0.95;
5. modal efficiency exceeds the no-modal ablation with a paired 95% bootstrap
   interval strictly above zero;
6. first-attempt intervention accuracy exceeds the same ablation under the
   same interval rule;
7. the impossibility response has transition and exhaustive-state evidence;
8. modal decisions are operative on at least four held-out states per run;
9. the ablation has no modal-decision side channel.

These criteria support only the causal use of bounded possible/impossible
reachability in this synthetic family. A search cap produces `unknown`, never
`impossible`; only frontier exhaustion within explicit perceived frame bounds
licenses impossibility.

## Development result

All criteria passed on seeds 0–29. The isolated modal descendant completed
every run at the 26-action oracle minimum. The no-modal descendant won 40% of
runs and averaged 76% completion. Modal reasoning improved paired
first-attempt intervention accuracy by `0.56111` (95% bootstrap CI
`[0.50262, 0.62556]`) and efficiency by `0.67651` (CI
`[0.53365, 0.81270]`).

The canonical development report has file SHA-256
`44c1005a02cdbd4d7d47944266ac40bfbc7ca384a6a984235ef6f111b8a19536`
and embedded result SHA-256
`cc57f63e839958904fe10340d18c20a10d7b6ad0683e41bac61fb0ebee83efb7`.
An immediate second run reproduced the JSON byte-for-byte.

## Untouched confirmation result

All nine criteria passed on the single execution of seeds
120,000–120,029 after the protocol and implementation were frozen in commit
`6ecec4f`. The isolated modal descendant completed every run at the 26-action
oracle minimum. The no-modal descendant won 33.33% of runs and averaged 75%
completion within the 72-action budget. The default full policy averaged
96.67% completion and won 93.33% of runs, exceeding its frozen threshold.

Modal reasoning improved paired first-attempt intervention accuracy by
`0.50139` (95% bootstrap CI `[0.45972, 0.54972]`) and efficiency by `0.72810`
(CI `[0.58778, 0.86381]`). Every action was legal, training histories were
identical, impossibility responses retained transition and exhaustive-state
evidence, and the ablation emitted no modal decision.

The canonical report is `validation-v5-holdout.json`, with file SHA-256
`d44df73b84a021242842afcc320645a8cf3f9ee73848eb5ed4fe83d2cdfdb36b`
and embedded result SHA-256
`f40b50baba47a31645f6fa6cce3fe9ac187e4f20845bcd2cf4c7085718542f2b`.
No code or criterion changed after this result was viewed.

## Commands

Development:

```bash
.venv/bin/reflector validate --suite v5 --seed-start 0 --seeds 30 \
  --output validation-v5-development.json
```

Frozen confirmation:

```bash
.venv/bin/reflector validate --suite v5 --seed-start 120000 --seeds 30 \
  --output validation-v5-holdout.json
```
