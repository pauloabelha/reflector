# Reflector validation protocol v6

Status: frozen after development. Confirmation seeds have not been viewed.

V6 tests whether an evidence-backed comparison between context-typed
transformation systems predicts withheld operator effects and improves
held-out control. It does not test composition of comparisons, general
category theory, developmental fidelity, or ARC-AGI-3 performance.

## Identification strategy

Each run randomizes the mapping from action labels to four cardinal effects.
A canonical perceived marker-domain forces one observation of all four
operators and one adjacency-goal demonstration. A negative-control domain then
forces two non-collinear calibrations that cannot be related to the canonical
operators by any of the eight square symmetries.

Eight held-out marker-domains follow. In each:

1. two non-collinear actions are forced as calibration correspondences;
2. the effects of the other two actions remain unobserved in that domain;
3. a target appears whose oracle solution is one application of a randomly
   chosen withheld action;
4. the target, marker, square symmetry, action-label permutation, and withheld
   action vary by seed.

The comparison descendant identifies the unique square symmetry supported by
both calibrations, applies it to the corresponding observed canonical
operator, and plans with the resulting context-typed inferred operator.
Every inference records its source operator, typed comparison, calibration
evidence, and observed/inferred status. A later contradictory observation
rebuilds the comparison set and removes unsupported inferences.

An independent exhaustive checker verifies that no sequence of the observed
calibration actions within the shared depth-three planner horizon can reach
any held-out target, that the withheld action does reach it, that calibrations
are non-collinear, and that the negative control admits no square symmetry.

## Policies and causal ablation

- `full`: default Kaggle-exportable `SymbolicPolicy`;
- `comparison_transfer`: the same inference package with unrelated concepts,
  experiments, accommodation, legacy transformations, modal reasoning, and
  reflecting abstraction disabled;
- `no_comparison_transfer`: bit-identical to `comparison_transfer`, retaining
  every observed context operator, learned typed comparison, schema, forced
  action, progress event, and ordinary planner, but unable to infer operators
  by applying a comparison;
- `score_only`, `context_table`, and `seeded_random` baselines.

Both causal variants are ordinary serialized `MindConfig` descendants. The
inferred effects remain outside `SchemaStore`, so the ablation cannot receive
them through a shared prediction table.

## Leakage controls

For every causal run the report verifies:

- the fixed eight-action pre-test history and scalar progress are identical;
- no withheld context/action effect is observed before its first intervention;
- all eight withheld effects exist before intervention only in the enabled
  descendant;
- the disabled descendant contains zero inferred withheld effects;
- successful comparison plans explicitly name an inferred operator;
- the inconsistent negative domain has rejected comparison evidence and no
  inferred augmentation.

Action labels, canonical effects, held-out symmetries, marker identities, and
query order are independently shuffled per seed. Target direction alone does
not identify which action has that context-specific effect.

## Development revisions

The original v6 design rejected the existing complete pairwise-delta graph:
because it creates every mapping by construction, finite laws over that graph
cannot establish learned transfer. Implementation therefore introduced
separate perceived domains, observed operators, evidence-supported finite
system comparisons, and provenance-bearing inferred operators.

The first development report marked forced histories unequal because the
bookkeeping included held-out calibrations only for worlds reached by a
policy. The fixed pre-test histories were in fact identical. The metric was
corrected to separate the fixed learning phase from per-query calibration;
no environment transition, action selection, inference, threshold, or
confirmation seed was changed.

## Split, budget, and oracle

Development uses paired seeds 0–29. Confirmation uses seeds
150,000–150,029 and may be executed once only after implementation, metrics,
baselines, thresholds, tests, protocol, development artifact, and official
compatibility gates are committed.

The action budget is 96. The oracle is 32 actions: eight fixed training and
negative-control actions plus two calibrations and one decisive action for
each of eight held-out domains. Paired confidence intervals use the existing
deterministic 2,000-resample bootstrap.

## Preregistered support criteria

All twelve criteria must pass:

1. the independent environment oracle and leakage audit pass;
2. every emitted action is legal;
3. fixed forced histories are identical within paired seeds;
4. isolated comparison-transfer completion is at least 0.95;
5. default full-policy completion is at least 0.90;
6. comparison-transfer efficiency exceeds the ablation with a paired 95%
   bootstrap interval strictly above zero;
7. first-attempt intervention accuracy exceeds the ablation under the same
   interval rule;
8. no withheld effect was observed before its intervention;
9. all eight withheld effects were inferred before intervention;
10. the ablation inferred none;
11. at least eight plans using inferred operators were operative per run;
12. the negative-control comparison was rejected without augmentation.

Passing supports only direct causal comparison transfer in this finite
synthetic family. It does not support morphism-composition causality; that
requires an endpoint-valid `A → B → C` test with direct `A → C` evidence
unavailable.

## Development result

All criteria passed on seeds 0–29. Both the isolated comparison descendant and
default full policy completed every run at the 32-action oracle. The ablation
averaged 49.33% completion and won 3.33% of runs. Comparison transfer improved
paired first-attempt intervention accuracy by `0.81063` (95% bootstrap CI
`[0.72127, 0.89861]`) and efficiency by `0.98730` (CI
`[0.96190, 1.00000]`).

The canonical development report has file SHA-256
`95bd496cd10ec4194bec756d1fb54cbc2b7c5527989643898e106b9efda5fef6`
and embedded result SHA-256
`a6af4ded7b686fde30f5f590821c8e5c2216146a6b55af5bcb4656afa27bac12`.
An immediate second run reproduced the JSON byte-for-byte.

## Commands

```bash
.venv/bin/reflector validate --suite v6 --seed-start 0 --seeds 30 \
  --output validation-v6-development.json

.venv/bin/reflector validate --suite v6 --seed-start 150000 --seeds 30 \
  --output validation-v6-holdout.json
```
