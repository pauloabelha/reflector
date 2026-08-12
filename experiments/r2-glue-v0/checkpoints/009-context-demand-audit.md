# Checkpoint 009: context-demand audit

Time: 2026-08-12

## Question

Do recorded games provide repeated evidence that command scope plus intrinsic
entity type is insufficient to predict a rigid outcome, thereby warranting a
new context factor?

## Method

`audit_unresolved_contexts.py` reads immutable Arcade ledgers and replays R2's
exact component extraction, mutual-unique correspondence, rigidity gate,
intrinsic type pooling, and command scope. It never fits a workspace or updates
a model. Identical reruns are deduplicated by game, predecessor digest,
successor digest, and action.

## Result

- 101 deduplicated transitions were audited.
- Games represented: AR25, BP35, CD82, CN04, and DC22.
- Unresolved same-type heterogeneous rigid records: 0.
- Repeated unresolved signatures: 0.

The synthetic test remains useful proof that heterogeneous evidence fails
closed and is observable. It is not empirical support for a live context
factor. No sequence state, spatial bin, role, or other discriminator was added.

## Next

The observed cross-game bottleneck is semantic revision load: on DC22, explicit
failure turns continued to regenerate unrelated semantic products and copied
the failed state. A focused repair transport can be tested without granting the
model grounding or action authority.
