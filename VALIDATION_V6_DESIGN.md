# Draft validation v6: causal comparison transfer

Status: superseded by the implemented frozen protocol in `VALIDATION_V6.md`.
This file remains the preimplementation falsification design and rejection
boundary.

Validation v4 established causal use of transformation composition and finite
structural laws over a comparison graph. It did not show that a comparison
predicts an unobserved transformation or improves control. V6 must close that
gap without making action labels, geometry, ordinary plan failure, or a global
schema an alternate route to the answer.

## Candidate claim

A Kaggle-exportable symbolic descendant can:

1. construct distinct context-typed transformation systems;
2. infer an evidence-backed mapping between two systems from at least two
   independently observed corresponding operators;
3. apply that mapping to predict a held-out operator effect;
4. use the predicted effect in control; and
5. lose that advantage when comparison transfer alone is disabled.

This would be evidence for causal comparison transfer on a synthetic family.
It would not establish general category-theoretic cognition, Piagetian
developmental fidelity, or ARC-AGI-3 generalization.

## Proposed interactive family

Each micro-world contains the same movable/target roles plus a new persistent
context marker. Primitive action labels are permuted per seed. A canonical
world forces observations of all four cardinal action effects. A transformed
world changes every effect by one member of the finite square-symmetry group
while preserving action identity.

For every held-out marker:

1. two forced calibration actions reveal two non-collinear transformed
   effects;
2. neither remaining action effect is observed in that context;
3. the target can be reached efficiently only by selecting one of those
   withheld actions;
4. absolute positions, marker identities, action-label permutation,
   transformation, and requested withheld action vary by seed.

The comparison-enabled agent may infer the unique symmetry supported by both
calibration pairs, apply it to the corresponding canonical operator, and add
an explicitly inferred context-typed operator with a complete evidence chain.
The ordinary schema store may learn observed effects but may not receive the
inferred effect.

## Required representation change

The current `OperatoryTransformation` groups effects by action and vector and
retains a strongest subject. That is insufficient: it erases the domain in
which an operator is valid. V6 requires:

- an explicit transformation-system/domain identifier derived from stable
  perceived evidence rather than a benchmark-provided label;
- transformations typed by that domain;
- a comparison object whose domain and codomain are transformation-system
  identifiers;
- an executable preserved map, initially restricted to the eight finite
  symmetries of the square;
- support from at least two non-collinear operator correspondences;
- provenance distinguishing observed from inferred operators;
- contradiction handling that retracts or specializes a bad inferred map;
- bounded application and composition with endpoint checks.

The existing complete pairwise delta graph cannot serve as evidence for this
claim because it creates every comparison by construction.

## Identification and ablations

The primary pair must be ordinary serialized descendants:

- `comparison_transfer`: context-typed transformations and evidenced mapping
  application enabled;
- `no_comparison_transfer`: bit-identical, retaining perception, schemas,
  every observed context-typed transformation, ordinary planning, training
  actions, and progress, but unable to infer a withheld operator through a
  comparison.

Additional baselines:

- exact context/action table;
- global action-effect controller;
- score-only controller;
- seeded random;
- untyped similarity matcher that ignores domain/codomain endpoints.

At least one negative-control world must violate a previously supported map.
The full mechanism must refuse or retract transfer there; otherwise a positive
result could be indiscriminate rotational augmentation.

## Leakage tests required before development acceptance

An independent checker must establish all of the following:

1. training actions and scalar progress are identical within each paired seed;
2. held-out context/action/frame keys never occur in training;
3. the withheld effect is absent from the ablation's schemas and observed
   transformations before its first intervention;
4. action-label frequency and canonical ordering do not identify the answer;
5. target displacement alone is insufficient without a context-specific
   action effect;
6. ordinary planning has the same depth and expansion budget in both variants;
7. plan absence is identical before the decisive comparison transfer;
8. the inferred operator records both calibration correspondences and the
   source canonical operator;
9. mismatched endpoints and single-correspondence maps are rejected;
10. the negative control does not receive an inferred operator.

## Metrics and evidence

Before any confirmation run, freeze:

- an exhaustive environment oracle and fixed action budget;
- held-out first-intervention accuracy;
- completion and completed-run efficiency;
- mapping precision, abstention, and contradiction/retraction counts;
- number of correct inferred operators before intervention;
- paired bootstrap procedure and thresholds;
- development failures and revisions;
- official `bt11`, full tests, offline smoke, export, and source/report hashes.

Success requires a strictly positive paired confidence interval for both
first-intervention accuracy and efficiency, high completion by the isolated
comparison descendant and default policy, calibrated abstention on negative
controls, and zero inferred operators in the ablation. Merely passing finite
identity or associativity laws is not a success criterion.

## Composition extension

Only after direct comparison transfer is causally identified should a later
suite require a chain `A → B → C` whose `A → C` prediction is available solely
through endpoint-valid composition. The ablation for that extension must
retain both direct mappings and disable only their composition. Directly
computing the `A → C` symmetry from shared observations would invalidate the
test.
