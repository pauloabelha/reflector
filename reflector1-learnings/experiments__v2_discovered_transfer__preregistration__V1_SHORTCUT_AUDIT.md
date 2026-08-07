# V1 shortcut audit

Audit date: 2026-08-03. Source: `evaluation/two_level_experiment.py` and
`evaluation/two_level_preregistration.json`.

V1 is a valid pipeline test, but it cannot support the V2 discovery claim.
The following source-level evidence identifies the shortcuts that V2 must not
inherit.

1. `Experiment.equilibrate()` constructs the Level A literal and relational
   paths directly and emits `declared_equivalent=True`. Equivalence is not
   inferred from repeated action-conditioned evidence.
2. `run_condition()` constructs the Level B transfer path from the exact same
   composition schema used for Level A. The sole `Correspondence` maps a schema
   hash to itself, so the mapping is one edge and identity by construction.
3. The only learned relation is singleton legal-action selection. There are no
   visually grounded entities, intermediate role hypotheses, enabling evidence,
   or causal chain with two connected edges.
4. `FrozenLevel.success_action` and singleton `legal_actions` make the relevant
   action immediately available to the experiment harness. V2 may retain latent
   success state for scoring, but it must not expose it to learner inputs or use
   it to construct correspondences.
5. V1 has one hand-selected pair. It has no development/validation/blind split,
   no family-level aggregate criterion, and no protection against a favorable
   single instance determining the verdict.
6. V1 has no surface decoy, structural near-match, reversed relation,
   extra-condition, or genuine-novelty control. It therefore provides no
   false-positive transport evidence.
7. V1 has no structural-probing phase and no executable strategy for selecting
   an action that discriminates among competing correspondences.
8. V1's treatment win is primarily the result of replacing a literal selector
   with a registered-equivalent generic primitive. It does not demonstrate
   decomposition of an entangled schema or discovery of an independently
   testable intermediate.
9. The dashboard records phase events, but lacks pair/condition selectors,
   multi-edge paths, role evidence, false-mapping rejection, and aggregate
   family analysis.
10. V1 is deterministic and transactional, and its trace/replay, complexity,
    quote/eval, and regression infrastructure are reusable. Its pair definition,
    equivalence declaration, and transfer construction are not reusable as V2
    evidence.

V2 admission rule: no blind result may count as discovered transport if any
candidate edge, role assignment, or endpoint mapping was created from latent
environment labels, the pair manifest's control class, or an identity mapping
supplied by the harness.
