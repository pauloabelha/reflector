# Reflector current summary

Last updated: 2026-07-30

## Best verified result

Reflector's best complete, process-isolated 25-game public-development result is
**16.355448098096414 / 100**.

- Candidate: `candidate-40b2dad207199755` (`v82f`)
- Frozen source: `79a872ca0ed3fa40a98b185b3217e304d81dc68f`
- Coverage: 25/25 games
- Levels: **39/183**
- Games with progress: **13/25**
- Complete games: **3/25**
- Actions: **9,185**
- Report:
  [`reports/official-isolated-v82f-dihedral-bridge-400.json`](reports/official-isolated-v82f-dihedral-bridge-400.json)
- Candidate:
  [`candidates/v82f-dihedral-bridge-composition-400.json`](candidates/v82f-dihedral-bridge-composition-400.json)
- Report SHA-256:
  `a29e963af1dd3af31d6e7cf040b8d28e7006e9bbf1e5007ed02e32e714674f56`

Relative to the clean v74 restart at **14.450686193334509**, v82f changes only
`tr87`: it advances from 0/6 to **4/6**, scoring 47.6190476190 on that game.
All other game outcomes are exactly preserved. The aggregate gain is
**+1.904761904761905 points**.

## New accepted mechanism: demonstrated analogy algebra

V82f learns transformations from visible input/output demonstrations rather
than from a game-specific route. Its abstraction grew through four levels:

1. glyph class to glyph class under the eight square symmetries;
2. glyph class to variable-length output sequence;
3. sequence-to-sequence substitution;
4. relational composition through a latent bridge color.

On `tr87`, the frozen agent reproduced 4/6 twice with level actions
`[56, 45, 44, 38, 217, 0]`. The complete quality gate passed with 437 tests,
3 skips, Ruff, and mypy.

## Current development result

V84b replaces the plus-specific route with a common finite-domain rewrite
substrate. Translations and focus transfers are grounded morphisms whose
predicted and observed abstractions must form commuting squares. Landmark
embedding is a CSP, bounded A* compiles its primitive policy as an option, and
only MDL-positive option programs are retained without duplication.

Frozen candidate `candidate-ec8492354af28870` reproduced `re86` exactly twice:

- target score: **2.7777777777777777**
- target levels: **1/8**
- level actions: **`[24,376,0,0,0,0,0,0]`**
- improvement over v84: level 1 fell from 34 to 24 actions
- causal evidence per run: 173 commuting confirmations, zero commuting
  conflicts
- reports:
  [`r1`](reports/experimental-v84b-categorical-re86-r1-400.json) and
  [`r2`](reports/experimental-v84b-categorical-re86-r2-400.json)

This is a deterministic efficiency breakthrough but not promotion evidence:
level 2 still did not advance. Only two translation controls remained at the
end, five actions were quarantined, and the final diagnosis was
`constellation-structure-changed`.

V84c then completed mover masks under central symmetry, correctly preserving
the first diamond translation under crossing-mover occlusion. Its frozen target
run nevertheless remained exactly 1/8 at `[24,376,0,0,0,0,0,0]`. The next
falsifier was temporal: a moving diamond overwrote a landmark-ring center and
partially hid the stationary X, changing its one-frame color label and visible
centroid. The active v84d accommodation therefore filters perception through
already confirmed morphisms: goal domains and non-focused variables persist,
while only an exactly predicted focused center may update. The verified
25-game score remains unchanged.

V84d produced the first multi-level breakthrough. Frozen candidate
`candidate-6b06fcb776d9097d` solved `re86` levels 1–2 in `[24,36]`:

- target score: **8.333333333333332**
- target levels: **2/8**
- full action vector: **`[24,36,340,0,0,0,0,0]`**
- controls retained: four translations and one focus transfer
- causal conflicts/quarantines: zero/zero
- compressed option reuses: two
- report:
  [`reports/experimental-v84d-causal-filter-re86-r1-400.json`](reports/experimental-v84d-causal-filter-re86-r1-400.json)

This validates causal belief-state filtering once, but v84d is not promoted
until the target repeats and the accepted suite is preserved. Level 3 ended
with `constellation-layout-not-grounded`, which is the next accommodation
target.

Level 3 reveals three overlapping same-colored movers, so color is not an
object identity. V84e learned the first factor but failed when the second
factor's selector moved onto the same-colored line and became invisible. It
therefore remained 2/8. The active v84f generalization treats a predicted
same-color selector cell as bounded occlusion and restores the probe before
requiring the marker to reappear. It then solves a unique minimum-cost product
exact-cover CSP over all eight landmarks. Its inferred target anchors are
`(27,6)`, `(42,24)`, and `(18,30)` for the line, X, and diamond factors.

V84f validates that product construction end to end. Frozen candidate
`candidate-f47fa9c6dfffb810` solved `re86` levels 1–3 in
**`[24,36,56]`**, reaching **3/8** and target score
**16.666666666666664**. Level 3 used exactly the predicted 56 actions for
factor discovery, restoration, focus transfer, and compiled routes. The full
vector is `[24,36,56,284,0,0,0,0]`; no control was quarantined and no causal
conflict occurred. This is not promoted until reproduced and preserved.

Level 4 cross-binds differently colored movers and landmarks. The active v84g
compiler reconstructs a boundary-clipped plus by unbounded central symmetry
and solves a unique bipartite embedding: plus color 6 to landmark color 12 at
`(15,30)`, then X color 10 to landmark color 14 at `(39,30)`. The resulting
committed hierarchical option has 24 actions.

## Rejected branch

V83 tested distance-decreasing replay on an inferred one-dimensional track.
It was behaviorally active on `sc25` but remained 0/6 in 400 actions. The
endpoint was not the task goal. The mechanism is retained exact-off as a
negative result and is disabled in v82f/v84 candidates.

## Immediate objective

The verified score remains **16.3554480981 / 100**. Reaching 20 requires at
least **+3.6445519019** aggregate points. The current priority is to validate
derive level 4's relational object, reproduce every gain, then run
preservation/full-suite gates. The exact accepted package is submitted to
Kaggle using `KAGGLE.md` only after the verified aggregate reaches 20.
