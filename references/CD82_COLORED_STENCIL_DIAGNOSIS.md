# `cd82` colored-stencil diagnosis

Last updated: 2026-07-30

Status: trace-derived design hypothesis. No `cd82` inference path has been
implemented or accepted. The current accepted v67 agent remains at 0/6 on this
game.

## Conclusion

`cd82` is best modeled as symbolic colored-stencil composition, not as a
latent pose/check task. The smallest supported procedure language is:

```text
SelectPalette(attribute)
NavigatePose(relative_octant)
ApplyPrimaryTemplate
ApplySecondaryTemplate(component)
```

Every observed construction update is consistent with ordinary
last-write-wins overwrite in the selected palette attribute. The apparently
clipped 12-cell effects are applications of separate small outlined template
components, not exceptions to the overwrite law.

## Evidence boundary

The accepted v67 suite leaves `cd82` at 0/6 after 400 actions, three resets,
and `GAME_OVER`. Its generic frontier selects 397 actions;
select/apply/commit reports `no-structural-candidate`, and shape translation
grounds no goal.

The public human recording completes 6/6 in 153 actions with no reset. Its
derived per-level action vector is `[55, 6, 41, 18, 17, 16]`; the environment
metadata baseline is `[55, 8, 41, 21, 23, 23]`. These values are diagnosis
evidence, not an agent result.

The recording supports:

- boundary no-ops and reversible moves that ground an eight-pose perimeter
  controller without retaining numeric action IDs;
- palette interventions that change the selected marker and every active
  template fill while preserving geometry and construction;
- a plain apply role that preserves pose and palette while overwriting a
  construction mask;
- four cardinal half-plane primary masks and four inclusive diagonal
  half-plane primary masks, derived from normalized grid geometry;
- separate secondary outlined components at cardinal poses, whose normalized
  silhouettes project radially into the construction;
- order-sensitive overwrite composition, including useful steps that
  temporarily increase pixel disagreement.

At the observed 10×10 scale, cardinal and diagonal primaries occupy 50 and 55
cells, but those counts must never enter runtime logic. The implementation
must derive the predicates from the current construction dimensions.

## Relational grounding

The scene hypothesis is admissible only when all roles are unique:

1. Find two same-sized dense grid patches.
2. Identify the construction as the patch around which same-fill outlined
   components move; its invariant peer is the reference.
3. Identify the palette as repeated congruent enclosures with uniform
   payloads and one unique selection marker.
4. Require active-template fill to equal the selected palette payload.
5. Group exterior outlined components by octant relative to the construction.
6. Define the nearer or dominant component as primary and retain every other
   component independently.
7. Normalize colors to palette roles, coordinates to
   construction-relative cells, poses to octants, and plain actions to learned
   displacement/apply roles.

Any ambiguity in reference, construction, palette, selected attribute,
template grouping, component projection, pose, or action binding must abstain.

## Proposed symbolic records

```text
TemplateScene
  reference_grid
  construction_grid
  palette_roles
  selected_role
  template_group
  current_pose

TemplateComponent
  normalized_silhouette
  radial_sector
  radial_rank
  current_click_token

PoseEffect
  controller_role
  source_pose
  destination_pose
  support_contexts
  conflicts

StrokeGenerator
  application_role
  pose_class
  normalized_write_mask
  semantics = overwrite-selected-attribute
  support_contexts
  conflicts
```

## Effect induction

1. A construction-only change whose new values all equal the selected palette
   role proposes an overwrite mask.
2. Because already-equal cells hide part of that mask, treat the first changed
   set only as a lower bound.
3. Recolor and repeat in a distinct construction context to recover and
   prospectively confirm the full mask.
4. Never let a proposing transition confirm itself.
5. Promote D4 transfer only after a registered prediction succeeds under a
   non-identity pose transform.
6. A secondary component may be projected radially while preserving its
   tangential offset only when the placement is unique; require a later
   preregistered click to confirm it.

Plain actions that move the whole template group while preserving reference,
construction, and palette bind to relative pose transitions. Boundary no-ops
are topology evidence. The primary apply role is the plain token that changes
only the construction while pose and palette remain fixed.

## Planning

Search symbolic states `(construction, selected_role, pose)`. Successors are
exact palette selections, pose transitions, and overwrite applications.
Prefer bounded reverse last-stroke synthesis or A* over greedy Hamming
descent. Rebind every abstract step to a currently represented token before
issuance and require exact predicted successor equality afterward.

Initial caps:

- at most 16 strokes;
- at most 50,000 synthesis states;
- at most 64 enacted actions per level.

Any successor mismatch clears the plan and quarantines its implicated
generator for the level. Level advance clears all palette, component, target,
construction, and plan bindings. Controller or template-family knowledge may
persist only after it is re-grounded in the new scene.

## Remaining terminal ambiguity

Immediately before the human level-5 completion, applying the north secondary
fixes 12 cells while five displayed disagreements remain. Each disagreement
lies on a boundary shared by two confirmed diagonal half-plane templates. The
recording cannot distinguish:

1. equivalence of ownership on coincident diagonal boundaries;
2. a symbolic layer/program goal whose raster display loses provenance;
3. a narrowly boundary-tolerant checker.

Do not introduce broad pixel tolerance. The only admissible fallback goal is:

```text
exact construction equals reference
OR
every remaining disagreement lies on the shared boundary of two confirmed
diagonal masks and its value is one of those masks' selected attributes
```

Use the fallback only after exact synthesis fails, preregister progress before
the final application, and retire it immediately if the level does not
advance.

## Staged experiment

Stage 1 enables primary templates only:

1. apply one contrasting primary at the initial pose to propose its mask;
2. recolor and repeat at the same pose to confirm overwrite semantics and
   recover the full mask;
3. move to a transformed pose, preregister the D4 mask prediction, and apply;
4. run exact synthesis for levels 1 and 2 only.

Preregistered target: at least 2/6 levels within 80 actions, no reset, with the
exact-off v67 control unchanged.

Stage 2 adds separately grounded secondary components. Level 3 supplies the
first natural secondary proposal and later confirmation. Only after that gate
passes may the narrow boundary-equivalence hypothesis be tested on level 5.

## Required promotion tests

- translation, recoloring, palette-order, action-ID, and all D4 permutations
  preserve the abstract scene and plan;
- all ambiguous role assignments abstain;
- boundary no-ops never become movement effects;
- first evidence proposes and only a later preregistered transition confirms;
- same-color overlap cannot truncate a learned mask;
- cardinal, diagonal, and secondary masks work on several odd and even grid
  sizes;
- order-sensitive composition and temporary disagreement increases work;
- a synthetic level-3 analogue transfers under color/action/pose permutation;
- boundary equivalence accepts only the intersection boundary of confirmed
  diagonal masks and rejects one off-boundary mismatch;
- unexpected successor, absent token, palette drift, or level advance clears
  current bindings;
- two deterministic target repeats, accepted-game preservation, full suite,
  static literal audit, exact export, and both offline smoke paths pass.

## Expected leverage

A complete `cd82` result would add roughly four points to the 25-game average
if every accepted game is preserved. The trace therefore makes this the
highest-leverage grounded next mechanism, but only the staged primary-template
gate is currently justified.
