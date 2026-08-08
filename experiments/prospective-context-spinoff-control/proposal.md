# Proposal: Prospective Context Spinoff Control

## Question

Can a bounded specialization of an ambiguous R2 transition schema, using only
active predecessor bindings, change one real online action and avoid the
unspecialized choice?

## Diagnostic case

Use public game `ar25`, level 1. The established Reflector recording reaches
two of eight levels, so it demonstrates meaningful progress, but later spends
most of its budget on repeated ineffective actions. R2 already discovers the
game's generic binary outline/contrast relations without labels or a
game-specific recognizer.

## Frozen protocol

1. Replay the level-1 prefix from the existing real-game recording through the
   offline public environment and current R2 perception/runtime.
2. Hold out the transition that completes level 1.
3. Represent each predecessor only by R2 schema IDs that have current
   `Binding` records. Actions remain opaque `ACTION_n` symbols.
4. Install one general transition parent. Rank actions from its observed
   support; ties use the opaque action ID.
5. If the parent is ambiguous, search a bounded set of active depth-0 binary
   relation schemas. For each relation, test its presence and absence. Retain a
   condition only with at least two predecessor observations and a strictly
   purer action distribution than the parent. Deterministic score and schema
   hash break ties.
6. Preserve the parent, create one child by adding the selected predecessor
   condition, and link it with `specializes`.
7. At the held-out predecessor, compare parent-only and child-conditioned
   rankings. Execute each top action from independently reconstructed copies of
   the exact same game/level state.
8. Before the treatment action, issue one R2 prediction for a generic
   structural successor delta. Resolve it only after observing the real
   successor.

No game ID, level ID, coordinates, palette meaning, object role, or environment
source code may enter feature selection or ranking. Environment level progress
is used only as the external outcome measure.

## Success gate

Pass only if the discovered condition is predecessor-visible and non-game-
specific, the child changes the top action, the treatment executes that action
prospectively, and the real successor either improves prediction/progress or
avoids the baseline action's mistake. Report a negative result if any link in
that chain is missing.
