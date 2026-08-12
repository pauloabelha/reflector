# Checkpoint 017 — unified semantic affordance bridge

## Question

Can a semantic model propose a broad, action-free idea such as alignment,
fitting, complementarity, or enclosure and have that idea reach measurable
entities and control without a game-specific verb mapping, palette rule, fixed
route, or privileged object identity?

## Architecture implemented

1. `SpatialSetAffordanceProvider` computes an anonymous pre-semantic frontier
   from occupancy, boundary, enclosed negative space, and envelope negative
   space. It reports measurable opportunity statistics and scale bands, not
   entity IDs, semantic labels, desires, or actions.
2. Each opportunity carries an opaque reference and exact measurement template.
   Qwen may cite it, or construct a new bounded measurement with null provenance.
3. Provenance is checked modulo only declared algebraic symmetries. Operand
   order is quotiented for symmetric difference and overlap deficit, but remains
   meaningful for left/right unmatched residuals.
   Frontier ranking likewise quotients reversed entity pairs only for
   same-feature commutative hypotheses, preserving meaningful distinctiveness.
4. Qwen emits one five-field prose state plus typed goals and schema hypotheses.
   It supplies only a terminal target; R2 derives relation, observable,
   direction, and canonical terminal text from their single typed sources.
5. A total nonempty goal-write failure is not treated as abstention. The prior
   semantic state remains canonical and a bounded compiler diagnostic persists
   in the same R2 projection until a coherent write clears it.
6. Schema identity uses the same canonical measurement quotient as its linked
   goal. Structured schema ports remain abstract: situated `fNN` aliases cannot
   pre-bind actor or target.
7. The ordinary R2 recursive grounder binds roles over primitive or CAE spatial
   entities, the controller chooses an exact legal command, and environment
   settlement separately updates goal progress, mechanism evidence, schema
   evidence, role identity, and causal-entity induction.

## Live evidence

A fresh AR25 trace completed the whole vertical slice without an AR25-specific
prompt or rule. Qwen proposed `align` with a scene spatial-set residual. R2
grounded two 45-cell entities, admitted the hypothesis only as
`PROBE_ELIGIBLE`, selected opaque `ACTION_1`, observed a uniquely tracked target
translation `[-3,0]`, and settled residual 65 to 68 as regression while marking
the mechanism observed. CAE induced one seven-member OPEN composite with an
action-conditioned translation.

In the next unchanged trace, the same goal survived rejected Qwen
serializations and later reached `PLAN_ELIGIBLE`: environment settlement
recorded two strict progress confirmations and best residual 59. This is local
measured progress, not an environment-terminal result. The logs also exposed
and drove three generic interface repairs: duplicate terminal authority,
nonpersistent compiler diagnostics, and goal/schema identity drift under a
commutative operand swap.

## Verification

- 138 focused semantic, runtime, planner, and worker tests pass.
- The full suite passes all implementation tests.
- Its sole failure is the unchanged historical documentation test whose
  expected `experiments/parallel-cognitive-workspace-v1-16/artifacts/SUMMARY.json`
  is absent.
- `git diff --check` passes.
- Source review found no AR25 identifier, yellow/blue pairing, L-shape route,
  action sequence, or palette-specific rule in the new architecture.

## Truthful boundary

This checkpoint proves communication and epistemic gating across language,
measurement, grounding, action, effect learning, CAE, and settlement. It does
not prove that `align` is the correct interpretation, that the selected pair is
the game's intended pair, that a level was completed, that score increased, or
that the architecture transfers. Checkpoint 018 freezes this architecture and
tests those claims on games selected before observation.
