# Schema-mechanism implementation notes

These notes record implementation consequences derived from two locally
consulted sources:

- Gary L. Drescher, *Made-Up Minds: A Constructivist Approach to Artificial
  Intelligence* (MIT Press, 1991);
- Robert Matthew Ramstad, *A Constructivist Approach to Artificial
  Intelligence Reexamined*, MIT/LCS/TR-563 (1993).

The repository does not redistribute either source. These are paraphrased
engineering notes, not a substitute for the books or a claim of faithful
reproduction.

## Contracts adopted by Reflector

1. **A schema is a prediction, not an action command.** Context, action, result,
   reliability, and marginal attribution belong to the predictive model.
   Planning and action selection consume schemas but remain separate modules.
2. **Reliability and action dependence are distinct.** Sufficiency asks how
   often a result follows an activated schema. Causal attribution compares that
   rate with observed alternatives. Neither statistic is external goal value.
3. **Sensory novelty is not reward.** Frame or object change may justify an
   experiment, but only environment-grounded progress should train a
   goal-reaching controller. Reflector therefore separates result value from
   epistemic progress.
4. **Specific evidence may override a general prediction.** A family can
   transfer only when an evidence-backed shared context applies; negative
   evidence in the current context gates a global plan.
5. **Repeated successful chains may become composite actions.** Reflector
   compiles evidence-bearing, MDL-positive procedures and lets the planner
   select a currently applicable suffix. This is a bounded approximation of
   Drescher's controller, whose component choice also accounts for proximity,
   reliability, time, cost, divergence, reconvergence, repetition, and repair.
6. **Internal symbolic structure is not behavioral validation.** Ramstad's
   evaluation cautions that reproducing predictive structures does not by
   itself demonstrate useful goal-directed control. Reflector therefore
   requires interactive completion and efficiency ablations.

## Important non-equivalences

Reflector's current `synthetic_item` term is a compiled functional concept. It
is **not yet** Drescher's synthetic item: a reified validity condition of a
host schema with explicit on/off/unknown activation, implicit activation, and
duration semantics.

Reflector's `ProcedureAbstraction` is likewise not the complete composite-action
controller. It learns successful multi-step trajectories and can select an
applicable suffix, but it does not yet search a dynamically shifting network by
empirical proximity or maintain separate controller reliability.

These gaps are future hypotheses, not missing labels. Any implementation must
remain within the same offline, dependency-bounded `SymbolicPolicy` used by the
Kaggle submission.
