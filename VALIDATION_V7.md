# Reflector validation protocol v7

Status: confirmed on the untouched preregistered split.

V7 tests whether endpoint-valid composition of two independently evidenced
finite comparisons predicts a withheld operator and improves held-out control.
It does not test arbitrary morphism composition, unbounded categorical
reasoning, developmental fidelity, or ARC-AGI-3 performance.

## Identification strategy

Each of eight query chains contains three perceived operator domains:

```text
A --comparison over action pair P--> B
B --comparison over disjoint pair Q--> C
```

Action labels 1–5 are permuted independently per chain and seed:

- A observes the two non-collinear P actions and a query action T;
- B observes P and the disjoint non-collinear Q actions, but not T;
- C observes Q, but not P or T.

The A→B comparison directly infers T in B. The B→C comparison is independently
identified from Q. Because T in B is inferred rather than observed, direct
comparison transfer stops there. The composition descendant may apply B→C to
that inferred intermediate operator, producing T in C with a two-comparison
provenance path. The ablation retains A→B, B→C, every direct inferred operator,
and the same planner, but cannot use an inferred operator as the source of a
second comparison.

The target in C is placed so one application of composed T reaches Manhattan
adjacency. No observed C operator or directly inferred P operator can do so
within the shared depth-one planning horizon.

## Perceived linkage and leakage prevention

Domains are not globally comparable. Marker components act as perceived link
tokens:

- A contains token `AB`;
- B contains tokens `AB` and `BC`;
- C contains token `BC`.

The comparison learner enters linked mode when a bridge domain has multiple
tokens and then compares only domains sharing a token. Tokens are unique
across query chains. Thus A and C have no direct comparison edge, and an
unrelated chain cannot leak a direct map into C.

The independent environment audit verifies:

1. P and Q are disjoint and T belongs to neither;
2. both correspondence pairs are non-collinear;
3. A and C share no perceived link token;
4. observed/directly inferred one-step operators cannot reach the query goal;
5. composed T reaches it exactly under the operative adjacency predicate.

Runtime leakage checks additionally require that T was never observed in C,
that every enabled query has an inferred path of length at least two before
intervention, and that the ablation has no such operator.

## Policies and causal ablation

- `full`: default Kaggle-exportable `SymbolicPolicy`;
- `comparison_composition`: isolated comparison system with direct transfer
  and bounded composition enabled;
- `no_comparison_composition`: bit-identical, retaining both direct
  comparisons and all direct inference, but refusing inferred intermediate
  sources;
- `score_only`, `context_table`, and `seeded_random` baselines.

Both causal variants use `planner_max_depth=1`; concepts, experiments,
accommodation, legacy transformations, modal reasoning, and reflecting
abstraction are disabled in both. They are serialized `MindConfig`
descendants using the same Kaggle inference package.

## Development revisions

An initial design allowed comparisons between every domain. With several
chains present, an unrelated bridge could sometimes create a direct route
into C, invalidating composition identification. That design was rejected.
Perceived link tokens and a bridge-domain linkage rule were introduced before
the accepted development run.

The first target geometry used diagonal/king-move adjacency while the deployed
goal representation uses Manhattan adjacency. It was corrected before
development acceptance: the inferred diagonal operation now leaves exactly
one horizontal cell of Manhattan distance. The independent oracle checks the
same deployed predicate. No confirmation seed had been selected or viewed.

## Split, budget, and oracle

Development uses seeds 0–29. Confirmation uses seeds 180,000–180,029 and may
be executed once only after the implementation, oracle, leakage checks,
metrics, thresholds, baselines, tests, protocol, development artifact, and
official compatibility gates are committed.

Every chain requires twelve oracle actions: three A observations, one A
goal/switch action, four B observations, one B switch, two C observations, and
one decisive action. Eight chains give an oracle of 96 actions. The fixed
budget is 192. Paired confidence intervals use the existing deterministic
2,000-resample bootstrap.

## Preregistered support criteria

All thirteen criteria must pass:

1. the independent environment and topology oracle passes;
2. all emitted actions are legal;
3. fixed initial histories are identical within paired seeds;
4. isolated composition completion is at least 0.95;
5. default full-policy completion is at least 0.90;
6. composition efficiency exceeds the no-composition ablation with a paired
   95% bootstrap interval strictly above zero;
7. first-attempt intervention accuracy exceeds the ablation under the same
   interval rule;
8. no queried C/T effect was observed before intervention;
9. all eight enabled queries have a composed C/T operator beforehand;
10. the ablation has no composed query operator;
11. the ablation nevertheless retains direct inferred operators;
12. every composed provenance path has matching comparison endpoints;
13. at least eight plans using inferred operators are operative per enabled
    run.

Passing supports only bounded two-step causal composition in this finite
synthetic family.

## Development result

All criteria passed on seeds 0–29. Both the isolated composition descendant
and default full policy completed every run at the 96-action oracle. The
no-composition descendant averaged 74.17% completion and won 26.67% of runs.
Composition improved paired first-attempt intervention accuracy by `0.63976`
(95% bootstrap CI `[0.58270, 0.69294]`) and efficiency by `0.82299` (CI
`[0.70403, 0.92664]`).

The canonical development report has file SHA-256
`5e6270e571bf24f816c85446817df8518f5ecaddb089b9900c95f0d25d2d5073`
and embedded result SHA-256
`c33bb6736926cb725e80bbbb347d186d8bcd0943ef601405caa93e120020785d`.
An immediate second run reproduced the JSON byte-for-byte.

## Untouched confirmation result

All thirteen criteria passed on the single execution of seeds
180,000–180,029 after the protocol and implementation were frozen in commit
`004e509`. Both the isolated composition descendant and the default full policy
completed every run at the 96-action oracle minimum. The no-composition
descendant retained both direct maps and direct inferred operators, but
averaged 74.72% completion and won 40% of runs within the 192-action budget.

Composition improved paired first-attempt intervention accuracy by `0.63655`
(95% bootstrap CI `[0.59270, 0.67972]`) and efficiency by `0.69007` (CI
`[0.54010, 0.82000]`). The independent topology oracle, legality, fixed
histories, leakage checks, direct-inference retention, endpoint-valid
provenance, and operative composed plans all passed.

The canonical report is `validation-v7-holdout.json`, with file SHA-256
`c28bf8ac1b2bf40e75774d0ac33f31fbb2f01a17c58c2787610ed14d86fadb2a`
and embedded result SHA-256
`4c5276f0de13832543a11774c05f9bc211a0aaa57273b904d9ae6ac603f0b6f8`.
No code or criterion changed after this result was viewed.

## Commands

```bash
.venv/bin/reflector validate --suite v7 --seed-start 0 --seeds 30 \
  --output validation-v7-development.json

.venv/bin/reflector validate --suite v7 --seed-start 180000 --seeds 30 \
  --output validation-v7-holdout.json
```
