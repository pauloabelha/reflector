# Checkpoint 007: transition evidence pooling

Time: 2026-08-12

## Failure

DC22 contained many mutually unique invariant entities of the same intrinsic
type. Counting each instance separately allowed one intervention to contribute
many confirmations, overwhelm later contrary evidence, and inflate the
semantic transition packet.

## Repair

Unassigned rigid correspondences are grouped by intrinsic type within the
settlement. A unanimous delta contributes exactly one effect observation with
the agreeing entity count retained for audit. More than one delta contributes
no type-level observation because a missing role or context factor is required.

This rule does not merge evidence across interventions and does not affect the
stricter goal-role settlement path.

## Evidence

- Two agreeing synthetic instances produce one model-support increment and
  `entity_count=2`.
- Two heterogeneous synthetic instances of the same type produce no effect.
- DC22's first transition shrank from 32 entity-level records to 14 type-level
  records; multiplicities 11 and 8 were retained explicitly, and the genuine
  2-cell translation remained present.
- 133 focused tests pass; the full suite has 245 passes and one unchanged
  missing historical artifact.

No DC22 completion or score gain is claimed.
