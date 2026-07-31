# Reflector current summary

Last updated: 2026-07-30

## Best verified result

Reflector's best complete, process-isolated 25-game public-development result is
**20.418940161588477 / 100**.

- Candidate: `candidate-07d24ee8acf946c9` (`v84m`)
- Frozen inference source: `5be5c9c`
- Frozen candidate commit: `f1232e6`
- Coverage: 25/25 games
- Levels: **47/183**
- Games with progress: **14/25**
- Complete games: **3/25**
- Actions: **9,185**
- Report:
  [`reports/official-isolated-v84m-grouped-dihedral-400.json`](reports/official-isolated-v84m-grouped-dihedral-400.json)
- Candidate:
  [`candidates/v84m-grouped-dihedral-analogy-400.json`](candidates/v84m-grouped-dihedral-analogy-400.json)
- Report SHA-256:
  `4823d8a358e7798293887ec8eaafd96041b4a5655f7b4da9154b7a7894bfc7c7`

Relative to accepted v82f, v84m changes exactly two games. `re86` advances
from 0/8 to **7/8** at `[24,36,56,44,63,57,120,0]`; `tr87` advances from 4/6
to **5/6** at `[56,45,44,38,55,162]`. All other 23 score/action vectors are
exactly preserved. The aggregate gain is **+4.063492063492063 points**.
The promotion gates pass: 461 tests pass with 3 skips, Ruff and mypy are clean,
both network-disabled smoke paths pass, and the prize audit reports technical
readiness. V84m is the accepted local candidate.

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

V84g executed that positional option but remained 3/8. The falsifier was
causal: reference swatches repaint a mover on contact. A manually derived
color-state route painted the plus `6→12`, painted the X `10→14`, avoided
later destructive swatches, and solved level 4 in 44 actions. The active v84h
planner therefore runs bounded A* over `(anchor,color)` and compiles the same
44-action paint-and-embed option.

V84h has now validated that accommodation behaviorally. Frozen candidate
`candidate-ff5318e279917649` solved `re86` levels 1–4 in exactly
**`[24,36,56,44]`**, reaching **4/8** and target score
**27.77777777777778**. The complete 400-action vector is
`[24,36,56,44,240,0,0,0]`; level 4 took exactly the predicted 44 actions.
The immutable report is
[`reports/experimental-v84h-paint-re86-r1-400.json`](reports/experimental-v84h-paint-re86-r1-400.json),
SHA-256
`20948ea86de811784a896085e831fd98cc83983288f6044b5a5093c1a3484ab6`.
This remains experimental pending an exact repeat and preservation gate.

Black-box level-5 analysis has produced the next structural breakthrough. The
scene is a coproduct/product composition rather than one mover per landmark
color: the X and plus must both be painted 9 and jointly cover the six
color-9 landmarks, while the diamond must be painted 8 and cover four
color-8 landmarks. Two of the latter centers render as color 12 only because
the current plus occludes them. A joint latent-color exact-cover CSP has one
minimum-cost geometric assignment—X `(30,15)`, plus `(33,51)`, diamond
`(51,36)`—and its paint-aware public-wrapper program solved level 5 in
**63 actions**. This is diagnostic evidence, not yet an autonomous candidate
result. V84i grounded all three options and issued 63 option selections, but
five lower-level paired-object actions interrupted the plus option; it
therefore remained 4/8. The active correction gives a committed hierarchical
option arbitration priority until completion, preserving its atomic
semi-Markov semantics.

V84j validates both accommodations end to end. Frozen candidate
`candidate-fd6a1798e5f36721` autonomously solved level 5 in exactly the
predicted **63 actions**, reaching `re86` **5/8**, target score
**41.66666666666667**, and full vector
`[24,36,56,44,63,177,0,0]`. The report is
[`reports/experimental-v84j-committed-composite-re86-r1-400.json`](reports/experimental-v84j-committed-composite-re86-r1-400.json),
SHA-256
`90a5b9ed938a63e63ff7004b26969b28b419cf39d6b7e6c834ee3cb387c4a24a`.
This remains experimental pending repetition and preservation.

Level 6 has also yielded a compositional black-box solution. Its apparent
deformation is a factored product: a plus consists of two conserved 25-pixel
segments under one shared action, while obstacle contact can hold one factor
and move the other; the 72-pixel square is a conserved-perimeter loop. The
landmarks specify a relative segment offset `(-9,+9)` and a 10×28 loop, both
derived from visible constraints. A 57-action program—35 cross-factor actions,
two focus transfers, and 20 loop actions—solved level 6 through the public
wrapper. Autonomous compilation is the active target.

V84k validates that compiler autonomously. Frozen candidate
`candidate-93770ad218d4a821` solved level 6 in exactly the predicted
**57 actions**, reaching `re86` **6/8**, target score
**58.333333333333336**, and vector
`[24,36,56,44,63,57,120,0]`. Report
[`reports/experimental-v84k-deformable-re86-r1-400.json`](reports/experimental-v84k-deformable-re86-r1-400.json),
SHA-256
`3655b3e259cde1f2f2ee8d50b19c5344d49042bccef884939617fe75b0ac4f71`.
This remains experimental pending repetition and preservation.

Level 7 black-box interventions expose a still more compressed construction.
The three visible movers are not new indivisible shapes: they are a 19×19
cross, a 37×19 cross, and a 13×13 conserved-perimeter loop. Translating the
occluded movers apart reveals four line factors. The target landmarks admit a
single economical factorization, but an initial cross-object recombination
hypothesis fails the obstacle/boundary reachability CSP. The simpler reachable
model preserves object identity: the 37×19 cross shears internally to cover
the color-8 target, the 19×19 cross shears by nine pixels to cover color 11,
and each cross receives one color. The loop maps to the two opposite color-9
corners of a 19×7 rectangle, whose perimeter equals the original loop's 48
pixels. Thus level 7 composes factor separation, paint-state routing, exact
cover, and within-object recombination. A bounded general compiler and
public-wrapper route remain to be validated.

The perimeter-48 loop has a 32-action paint/deformation route to the 19×7
color-9 target. Same-color occupancy checks have rejected two apparent cross
shortcuts. The 45-action small-cross route places its horizontal factor but
leaves the vertical factor at `y=39…57`; `(45,30)` merely remains visible.
The first fully occupied color-11 route is therefore the earlier **56-action**
construction, covering `x=36…54` and `y=30…48`. Likewise, proposed 34/36
action color-8 routes merely preserve visible landmark centers. The first
fully occupied color-8 construction takes **50 actions**. These correct
options exceed the remaining 120-action level budget, so route/prefix
compression and the actual level transition remain unvalidated.

A diagnostic extended-horizon composition has now crossed the real level
boundary. Executing the fully occupied 56-action small cross, 32-action loop,
50-action asymmetric cross, and two focus transfers completed level 7 at
total action **420** (140 actions within the level). This is not an admissible
400-action candidate, but it validates the complete factor/paint/deformation
model and isolates a 40-action efficiency deficit. The next gate is a shorter
representative of the same proven morphism, followed by autonomous
compilation at the official horizon.

Exact-span macro minimization has now closed that deficit. The small cross
compresses from 56 to **38 actions**, and a coupled two-count loop reduction
compresses 32 to **30** while preserving its full perimeter target. Together
with the exact 50-action asymmetric cross and two focus transfers, level 7
takes exactly **120 actions**. A fresh public-wrapper composition completed
level 7 at total action **400**, yielding the diagnostic vector
`[24,36,56,44,63,57,120,0]` with 7/8 levels. This is the first valid
seven-level route; autonomous compilation, repetition, and suite preservation
remain pending.

V84l validates the compiler autonomously. Frozen candidate
`candidate-5f09e48c374d0a52`, inference fingerprint
`baa58d2d8ef66726aa32e32ebef080e0297e32b0dfd24f15b468e83982f0abe8`,
reached `re86` **7/8** at exactly
`[24,36,56,44,63,57,120,0]`, target score
**77.77777777777779**, and 400 actions. Report
[`reports/experimental-v84l-factor-bundle-re86-r1-400.json`](reports/experimental-v84l-factor-bundle-re86-r1-400.json),
SHA-256
`438623478f7e156b806ba606b4450659cb1ebd6012fcc18c5372a7f2dba53689`.
This raises the unchanged-suite projection to about
**19.4665592092 / 100**. Repetition and preservation remain pending, and the
20-point gate is still short by about **0.5334407908**.

An independent fresh-process rerun reproduced the same score and exact vector.
Its report is
[`reports/experimental-v84l-factor-bundle-re86-r2-400.json`](reports/experimental-v84l-factor-bundle-re86-r2-400.json),
SHA-256
`d590a183d2510acfcca9ac427bf1a9f7985a13ade408b598ae82c60f30832c9d`.
The target gain is therefore deterministic twice; full-suite preservation is
still pending.

The minimum remaining cross-game opportunity is now grounded on `tr87`.
V84l exactly preserved v82f there: **47.6190476190**, 4/6 levels,
`[56,45,44,38,217,0]`. Report
[`reports/experimental-v84l-tr87-r1-400.json`](reports/experimental-v84l-tr87-r1-400.json),
SHA-256
`ddd487d02ad3665aa9af0a3a958e51a85cc7f30c49797fc8ccf3a987c2c83217`.
The fifth panel reverses the earlier interface. Two fixed five-glyph rows are
partitioned by the run-length signature of editable alternating-color rows:
`(1→1),(1→2),(2→1),(1→1)`. This is an isomorphism between a flat sequence and
a coproduct of eight editable groups, not a new color- or coordinate-specific
rule. A 19-action public-wrapper program derived from that partition completed
level 5 at total action **202**.

The generalized grouped-dihedral compiler now infers the real held-out frame
as eight groups of lengths `[1,1,1,2,2,1,1,1]`, transports each fixed glyph's
dihedral class through the unique partition, identifies the unique selected
group, and finds seven unsatisfied groups. It has strict size, color,
partition-sum, ordering, and selector-uniqueness abstention gates. Synthetic
isomorphic and malformed controls, Ruff, mypy, and the Kaggle contract pass.
Autonomous target repetition and suite preservation remain pending.

V84m passed its first autonomous target gate. Frozen candidate
`candidate-07d24ee8acf946c9`, inference fingerprint
`53729246c43ad6aadcc4fa4ba95a08510f0b200c83d08bd9ea3518816803e36d`,
reached `tr87` **5/6** at `[56,45,44,38,55,162]`, score
**71.42857142857143**, and 400 actions. The grouped compiler completed level 5
in **55 actions**, safely below the 66-action efficiency cap. Report
[`reports/experimental-v84m-grouped-tr87-r1-400.json`](reports/experimental-v84m-grouped-tr87-r1-400.json),
SHA-256
`792ba1d27c432e8c7c704afed86a6db9e42cecbeb572a8982bd3c31ea9499674`.
Combining this measured target result with the unchanged v82f suite and v84l
`re86` result projects to about **20.4189401616 / 100**. Independent repetition
and the full suite remain mandatory.

An independent fresh-process v84m rerun reproduced the exact score and vector.
Report
[`reports/experimental-v84m-grouped-tr87-r2-400.json`](reports/experimental-v84m-grouped-tr87-r2-400.json),
SHA-256
`3fdc513156c80b8a1d1437b3f173fd97cd64bbe21271e931228850528a004bb3`.
The grouped gain is deterministic twice. The full 25-game process-isolated
preservation run is now the only remaining score gate.

## Rejected branch

V83 tested distance-decreasing replay on an inferred one-dimensional track.
It was behaviorally active on `sc25` but remained 0/6 in 400 actions. The
endpoint was not the task goal. The mechanism is retained exact-off as a
negative result and is disabled in v82f/v84 candidates.

## Immediate objective

The verified score is now **20.418940161588477 / 100** with full coverage and
exact non-target preservation. The exact Kaggle export hashes are candidate
`b32d3b48f358951abf22a375faab92b0a6ea705aa1721f1b3d9ecc2098f85e54`,
overlay
`7e4ddf76c500396b7dc711977677d7aeeac068e354058124dbbbf390346d2e19`,
and notebook
`875cc88012b24008103017e98d64c6e49e9ae496c371da9c0eb4bbcefa290064`.
Submit this exact candidate using `KAGGLE.md`; do not attribute the resulting
hidden score until Kaggle returns one.

Kaggle notebook `pauloabelha/reflector-arc-agi-3-v84m` version 1 completed
successfully with internet disabled and emitted `submission.parquet`. Its
competition submission request returned HTTP 400 because the one-per-day
allowance had already been consumed by v74 submission `55123277`, which is
`PENDING`. No v84m competition submission ID exists yet. Historical v65b
submission `55113224` is now `COMPLETE` with Kaggle public score **0.02**;
its private score remains unavailable.

## Current experiment: compressed backward progress credit

A new immutable audit of all 25 v84m cognitive streams records 43 observable
level transitions and 75 failure/reset events. All failures followed generic
exploration: 40 were attributed to hierarchical action-family selection and
35 to untried-state selection. The dominant four-action motifs were four
consecutive hierarchical selections (39 failures) and four consecutive
untried selections (34 failures). Report
[`reports/v84m-progress-failure-signatures-v1.json`](reports/v84m-progress-failure-signatures-v1.json),
SHA-256
`c5dd2d22b0fc21ac5652be900745da835ff23e09a39f4f1923aa5c1bd07b9614`.

The next minimal offspring activates the existing exact-off shortest-progress
compiler. After a level advance it finds only the shortest observed non-reset
path, replaces consecutive identical grounded action roles with repetition
counts, and may transport that bounded option into the next level for at most
64 actions. It stores no game identifier, frame, coordinate route, or public
solution. The falsifier is strict: it must shorten or extend progress without
regressing any accepted vector. Failure-conditioned avoidance remains a
separate future hypothesis.
