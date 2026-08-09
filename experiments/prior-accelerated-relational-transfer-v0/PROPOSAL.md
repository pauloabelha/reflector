# Prior-Accelerated Relational Transfer v0

## Question

Can a relational schema learned from the successful first level of `ar25`
accelerate a fresh first level in another real ARC-AGI-3 game, and can the same
mechanism accept an explicitly external explanation without confusing it with
endogenous knowledge?

This is a small transfer diagnostic. It is not a general ARC planner and it
must not be promoted into `src/reflector2` on this result alone.

## Frozen information boundary

The source learner may see only the chronological states, opaque actions, and
level-completion boundary of the successful `ar25` level-1 recording. It may
use R2's generic structural vocabulary and raw geometry, but no target state,
target action outcome, target game identity, or human note.

The external arm receives one immutable structural prior translated from the
human note. It receives no invented evidence count. The scratch and self-built
arms never see the human note. Source action IDs, bindings, colors, frame IDs,
coordinates, and game IDs are forbidden from transferred schema identity.

Target-local action-effect observations may attach a local opaque action to a
transferred action-agnostic consequence. Such confirmation never rewrites the
source schema or makes an external proposal endogenous.

## Source schema language

Candidate source schemas are bounded combinations of existing neutral R2
relations and generic geometric effects:

- `SameOutline(a,b)`;
- `SameInteriorLayout(a,b)` and `DifferentInteriorLayout(a,b)`, derived by
  composing a figure's contained value-regions and normalized cell positions;
- a joint displacement correspondence over multiple figures;
- preservation, increase, or decrease of a translation-alignment residual;
- a real level-completion boundary.

A self-built control schema is admitted only if a suffix ending at real source
progress contains at least two consecutive transitions reducing the same
relational residual, with a stable coupled-intervention role signature. If
overlap merges the figures and hides direct correspondence, a stable repeated
intervention may extrapolate the already measured decrement only to the real
progress boundary; this occlusion is explicit in the audit. The stored evidence
is the chronological source transition indices, never target data.

## External explanation

The external prior is frozen separately and marked `externally-proposed`:

> When three figures share an outer structure, two share one interior
> structure, and a third differs, consequences that align the two matching-
> interior figures while preserving a coupled intervention may be control-relevant.

This is represented with the same structural atoms as the learned schema. The
natural-language sentence is annotation only and never enters schema identity.

## Mechanical targets

Selection uses only each public recording's first rendered grid and initial
legal action list. It does not use notes, later packets, progress, recorded
actions, or treatment results.

Positive target:

1. exclude `ar25`;
2. require at least two legal actions;
3. form same-outline groups and partition each by its normalized non-primary
   interior-cell layout (palette identities are ignored);
4. require a group of at least three figures, at least one same-layout pair,
   and at least two different-layout pairs;
5. compare each qualifying group with the source group's tuple: group size,
   largest layout-class size, number of layout classes, and number of
   different-layout pairs;
6. minimize the tuple of absolute differences in that order, then break ties
   by lexicographic game ID and outline hash.

Negative control:

1. exclude the source and positive target;
2. require at least two legal actions;
3. require zero `SameOutline` bindings;
4. choose the first qualifying game in lexicographic order.

The selected IDs, source distance, coarse R2 counts, and first-frame layout
counts are written before any target execution. The richer layout relation is
generic and source-derived: it was added during design because the coarse
`InteriorContrastCount` audit collapsed spatially different interiors.

## Arms

Each target receives four fresh, process-isolated runs:

1. `scratch`: no transferred or external schema;
2. `self_transfer`: frozen action-agnostic source schema;
3. `external`: frozen external proposal;
4. `combined`: both, retaining separate provenance.

All arms share the same deterministic fallback: least-used legal simple action,
then smallest opaque action ID. A prior may override only after its relational
antecedent binds and a target-local action consequence predicts a strict
decrease in the bound alignment residual. Otherwise it abstains exactly to the
fallback. Complex coordinate actions are epistemic abstentions in v0.

## Execution and checkpoints

- Two targets × four arms = eight real ARC runs.
- Maximum 32 actions per run.
- Independent processes, at most four simultaneous workers.
- One runtime/environment per run; no mutable graph or controller sharing.
- Atomic `latest.json` checkpoint after every action.
- JSONL trace is flushed after every action.
- Resume reconstructs the environment by replaying the checkpointed opaque
  action history and verifies chronological frame hashes.

## Outcomes

Primary:

- first-level completion;
- actions to first completion;
- peak completed levels;
- failed actions before prior confirmation;
- action savings versus scratch;
- regression on the negative control.

Secondary:

- whether each schema bound;
- local action-consequence confirmations;
- prior overrides and abstentions;
- new target-local consequence records;
- whether self-built and external schemas make the same decisions.

## Interpretation

`PROMISING` requires either:

- a prior arm completes the positive target when scratch does not; or
- a prior arm completes it with at least 25% fewer actions than scratch;

and no prior arm performs worse than scratch on negative-control first-level
completion or peak completed levels.

`NEGATIVE` means the relational prior binds and causes interventions but every
prior arm fails to improve the positive target, or a prior regresses on the
negative control. Otherwise the verdict is `INCONCLUSIVE`.
