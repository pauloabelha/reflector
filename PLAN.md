# Reflector persistent plan

Last updated: 2026-07-31

Conceptual research handoff: read `INSIGHTS.md` after this plan and before
starting the next experiment. It records the current external ARC-AGI-3
evidence, the project's earned claims, and the architectural implications.

## End state

Evolve a purely symbolic, open-source ARC-AGI-3 agent until it scores
competitively on the actual Kaggle competition while preserving this invariant:

> Every accepted descendant is the same offline package used by local
> development, official public-game evaluation, replay, population evaluation,
> and Kaggle inference. No translation or manual policy rewrite is allowed.

The goal is not complete. A local public-development gain, a Kaggle smoke test,
or a synthetic validation result is progress—not proof of competitive hidden
generalization.

## Authoritative current state

- Branch: `codex/v74-fresh`
- Participant repository: `git@github.com:pauloabelha/reflector.git`
- Upstream starter remote: `https://github.com/arcprize/ARC-AGI-3-Agents.git`
- Last pushed participant-remote commit: `5523abc`
- Accepted candidate: `candidate-2d9cadd5859ce47d`
- Accepted agent: Reflector v94b
- Frozen inference source commit: `203fa2e`
- Frozen candidate commit: `203fa2e`
- Inference fingerprint:
  `80d2c3f7c3a1842fefd0b29fb43eb5968b61eecbc66e0462def3e6bee7dc1db8`
- Verified public-development report:
  `reports/official-isolated-v94b-atomic-temporal-resource-400.json`
- Verified score: `20.65827051873133`
- Accepted coverage: 25/25 games, 9,185 actions
- Verified completions: 49/183 levels across 15 games; 3/25 games complete
- Kaggle submissions: v65b `55113224` complete at public score `0.02`; v74
  `55123277` pending
- V84m Kaggle notebook: `pauloabelha/reflector-arc-agi-3-v84m`, version 1,
  complete with `submission.parquet`; competition submission blocked by the
  already-consumed daily allowance, so no v84m submission ID exists
- V94b Kaggle notebook: `pauloabelha/reflector-arc-agi-3-v94b`, version 1,
  complete with `submission.parquet`; competition submission was attempted but
  blocked by the daily quota occupied by pending v74, so no v94b submission ID
  exists
- Kaggle public score: `0.02` for v65b only; v74 pending; v94b unsubmitted
- Kaggle private score: unavailable
- Canonical human-readable report: `REAL_GAMES_REPORT.md`
- Maintenance state: canonical code is organized under `reflector/core/`,
  `reflector/runtime/`, `reflector/research/`, and `reflector/evolution/`.
  Legacy top-level imports remain compatibility aliases.

## Rejected experiment: v95 confirmed cross-level action algebra

Parent: accepted v94b `candidate-2d9cadd5859ce47d`.

The accepted trace conserves the same four primitive translations and the same
25-cell colored-body partition through `ls20` levels 1--3, but v94b relearns
the algebra after each level. This costs part of the 21-action temporal horizon
and leaves only 143 actions for level 3.

V95 retains a complete, grounded action algebra only as an inactive hypothesis.
After the level transition it:

1. waits through any whole-scene discontinuity;
2. canonicalizes the mover's colored mask up to bijective color renaming;
3. checks one mapped action against both the inherited partition signature and
   inherited displacement;
4. activates all laws only if that commuting square holds;
5. rejects the inherited algebra atomically on either mismatch and learns only
   the current observation.

This is bounded knowledge compression with an explicit causal falsifier, not
unconditional cross-level leakage. Unit and transformed controls pass; offline
replay confirms that authority first becomes prospective on level 2, where it
changes the next action with 15 inferred budget units remaining.

Frozen candidate `candidate-304a6d8e5158b3ae`, source commit `32961b4`,
fingerprint
`f4df3a58770ab1aa59a766a474aae74ceade91b7a6f36a8686f27d3b752e1362`,
is rejected after the first target. It preserved 2/7 but regressed the vector
from `[17,240,143,0,0,0,0]` to `[17,277,106,0,0,0,0]`. The two transfer
checks confirmed with zero rejections, so the naturality predicate was not the
failure.

The causal divergence is precise. V95 activated at level-2 action 6 and
scheduled a reset resource before observing any local operator-induced phase
transition. That option reached the apparent terminal route one action short
and lengthened the first failed retry by 37 actions. After explicit retries
cleared the inherited algebra, v95 and v94b executed the same 106-action failed
retry and the same 68-action successful retry.

Next minimal hypothesis:

- retain prospectively confirmed primitive laws as navigation authority;
- treat resource scheduling as a dependent morphism requiring at least one
  current-level operator transition;
- before that evidence, permit only direct navigation to the operator;
- preserve every existing budget, path, atomicity, and falsification bound;
- reject unless a frozen target improves v94b without losing a level.

This hypothesis is frozen as v96 `candidate-b7142ea72796ed4f`, generation 51,
with inference fingerprint
`f3ee4ccbad8cf6d60f679cdc80b963680bcc64efdcd832874e6ff823a14159a1`.
The candidate is the accepted v94b genome with only the source-level dependent
authority condition changed. Focused tests pass, including a paired
before/after-local-effect resource-scheduling control. Run the full quality
gate, freeze the source commit, then evaluate one isolated `ls20` target.

## Why the accepted agent wins what it wins

| Mechanism | Causal real-game evidence |
| --- | --- |
| Epistemic state-graph exploration | v14 exact equal-budget control scored zero; enabled agent solved `r11l` L1 in 18 actions and `lf52` L1 in 34. |
| Failure-driven click-ontology accommodation | v18 preserved both v14 wins and added `tn36` L1 in 123 actions; unconditional multicolor grouping had regressed `r11l`. |
| Within-frame local relation induction | v20 preserved v18 and added `ft09` L1 in 4 actions by inducing same/different constraints from solved panels. |
| Cross-level relation retention | v21 preserved v20 and added `ft09` L2 in 7 actions on an overlapping layout with no solved example. |
| Mature-stall causal role reuse | v29 preserved all eight v25 levels at exact action counts and added `lp85` L1 in 37 actions; the source-matched control remained at zero on `lp85`. |
| Marker-relative cyclic transport composition | v30 learned a goal relation only from level progress, preserved every v29 action count, and solved `lp85` L2 in eight composed transport actions; its exact-off full control reproduced v29. |
| Grounded graph-cycle transport | v31 bound controllers only after exact conserved cycle shifts, planned over shared junctions, preserved every v30 action count, and solved `lp85` L3 in 54 actions. |
| Parameterized select/apply/commit | v32 inferred an ordered attribute template and matching selector/target bindings, preserved every v31 action count, and solved `sb26` L1 in 9 actions. |
| Nested container traversal | v35 inferred an occupied target-lattice slot as a uniquely attribute-matched child link, expanded the child, resumed the parent, preserved every v32 action count, and solved `sb26` L2 in 15 actions. |
| Enclosure-grounded sibling composition | v37 represented same-height sibling containers as separate enclosure objects, preserved every v35 action count, and solved `sb26` L3 in 15 actions. |
| Evidenced shape-goal translation | v39 learned plain-action translations from rendered effects, matched one mover to a unique stationary shape goal, preserved every v37 action count, and solved `ar25` L1 in 17 actions; its exact-off control remained at zero there. |
| Relational-phase-conditioned translation | v40 reassigned rare markers between persistent hosts, quarantined phase-A action semantics, re-probed in phase B, preserved every v39 action count, and solved `ar25` L2 in 17 actions. |
| Substrate-topology belief planning | v42 inferred 28 origin-relative topology nodes and 10 uncertain gates on `g50t`, used two safe information actions to advance a blocking autonomous gate, preserved all 16 v40 levels exactly, and solved `g50t` L1 in 29 actions twice. |
| Failure-conditioned cross-retry accommodation | v47b preserved the accepted zero-failure mature-stall path, suppressed reuse after one ambiguous failure, and conserved capped maturity plus action-family fairness only after two failures; it preserved all 17 v42 levels exactly and solved `sp80` L1 at action 196 twice. |
| Paired-object contact planning | v49b learned ordered joint effects for one reflected congruent pair, planned over independently blocked anchors, and treated planned contact as a bounded latent intermediate; it preserved all 18 v47b levels exactly and solved `m0r0` L1 at action 20 twice. |
| Compressive compact-component frontier | v64b admitted an object-graph vocabulary only when it did not expand the current perceptual ontology, preserved all 19 v49b level/action vectors, suppressed the 87-for-47 expansion that had regressed `tn36`, and solved `vc33` L1 at action 262 twice. |
| Bounded connector-graph synthesis | v65b selected a unique minimum-cost assignment over visible ordered references, nested containers, fixed payloads, and connector inventory only as a legacy fallback or under a strict repeated-reference dominance proof; it preserved every non-target trajectory and completed all eight `sb26` levels in 124 actions twice. |
| Learned lattice effects plus exact CSP | v66 grounded one regular repeated-actuator lattice, induced a relative binary click-effect law from two structurally distinct interventions, prospectively quarantined mismatches, and solved visible relation constraints exactly; it preserved every non-`ft09` trajectory and completed all six `ft09` levels in 162 actions twice. |
| Confirmed segmented permutations plus exact transport | v67 proposed a unique equal-pitch permutation from one rendered transition, preregistered its full-domain successor before a subsequent same-form action, promoted only after an exact match, and searched a bounded projected marker state; it preserved every non-`lp85` outcome and solved `lp85` L4 at action 71 twice. The confirmer need not yet be a spatially distinct controller. |
| Contiguous path cycles plus topology-grounded controllers | v68 inferred nested one-step rotations over a conserved uniform simple rectilinear slot path and distinguished identical controller sprites by endpoint/straight/corner context; it preserved every non-`lp85` score, level count, action total, reset count, and reported distribution while solving `lp85` L5 at action 50 twice. Level 6 exceeds the fixed slot bound and remains explicitly unrepresented. |
| Grounded primary colored-stencil composition | v69 uniquely grounded a congruent reference/construction pair, visible palette roles, and an outlined eight-pose template; learned controller roles only from rendered translations; and searched bounded exact programs of palette selection, pose navigation, and half-plane overwrites. It preserved every non-`cd82` accepted trajectory and solved `cd82` L1–L2 at `[12,6]` twice. |
| Secondary stencil and factored orbit composition | v74 independently grounded smaller overwrite components and factored cyclic direction from radial rank. It completed `cd82` 6/6 and reached `lp85` 6/8 while preserving all other v69 outcomes exactly. |
| Demonstrated dihedral analogy algebra | v82f inferred glyph-to-glyph, glyph-to-sequence, sequence-to-sequence, and bridge-composed relations under square symmetries. It preserved every v74 game exactly except `tr87`, where it reproducibly advanced 4/6 at `[56,45,44,38,217,0]`; the full suite rose to 16.3554480981 and 39/183 levels. |

## Current experiment: v84h causal paint-state constellation options

V84b is not promoted. Candidate `candidate-ec8492354af28870`, frozen at source
`5d64e5794c3720e14f2a7f7d3f430e359cf6992d`, reproduced `re86` exactly twice
at 1/8, score 2.7777777778, and `[24,376,0,0,0,0,0,0]`. This improves v84's
level-1 route from 34 to 24 actions but does not add a level.

The implementation now represents mover positions and finite landmark-
embedding domains as focused rewrite objects. Observed translations and focus
transfers earn authority only through commuting-square checks. A bounded A*
CSP compiler produces hierarchical primitive options; MDL-positive programs
are deduplicated before retention. Translated, reflected, color-renamed, plus,
X, diamond, and ambiguous-but-lattice-filtered synthetic cases pass.

Level 2 remains the falsifier. Each repeat recorded 173 commuting
confirmations and zero commuting conflicts, but ended with only two move
actions, five quarantined controls, and `constellation-structure-changed`.
V84c's central-symmetry completion removed the first crossing-mover mask
failure, but its frozen run still remained 1/8 at `[24,376,0,0,0,0,0,0]`.
Black-box replay exposed a second occlusion: a mover can overwrite a landmark
center and asymmetrically hide a stationary mover, corrupting both perceived
role and centroid. V84d now preserves goal domains and non-focused variables
under confirmed morphisms, while accepting a focused update only when its
center exactly matches the predicted displacement.

The first frozen v84d run passed that falsifier and is the first multi-level
result: `re86` reached 2/8 at `[24,36,340,0,0,0,0,0]`, score 8.3333333333.
All four translations and focus transfer survived, with zero quarantines and
zero causal conflicts. Two retained option programs were reused. Level 3 then
remained ungrounded for the remaining 340 actions.

Level 3 has three overlapping same-colored factors whose focus anchors cycle
through `(30,45)`, `(18,48)`, and `(45,48)`. One translated intervention
causally separates each factor mask. The resulting product exact-cover CSP has
one minimum-cost solution: target anchors `(27,6)`, `(42,24)`, and `(18,30)`,
covering all eight landmarks exactly once. V84e integrates bounded discovery,
strict exact-cover uniqueness, and the existing option compiler.

V84e's first frozen run remained 2/8 because the second factor's selector
translated onto the same-colored line and temporarily disappeared. The online
learner demanded a visible marker and repeatedly reprobed. V84f accepts only
the predicted same-color cell as selector occlusion and prioritizes the known
inverse restore before parsing focus again.

V84f passed the online gate. Its first frozen run solved level 3 in exactly the
predicted 56 actions, reaching `re86` 3/8 at
`[24,36,56,284,0,0,0,0]`, score 16.6666666667. All controls remained
authoritative with zero quarantines and zero causal conflicts. Level 4 is the
next concrete falsifier.

Level 4 has two differently colored movers, two landmark groups, reference
swatches, and a boundary-clipped selected plus. Geometry uniquely cross-binds
plus color 6 to landmark color 12 at `(15,30)` and X color 10 to landmark
color 14 at `(39,30)`. V84g completes symmetry beyond the frame boundary,
requires a unique minimum-cost bipartite binding, and commits the resulting
24-action two-mover option so intermediate X recoloring cannot erase identity.

V84g executed all 24 positional actions but remained 3/8. Swatch contact is a
causal paint transition, not nuisance recoloring. A black-box program that
first painted plus `6→12` and X `10→14`, then avoided all destructive swatches
while reaching the same embedding targets, solved level 4 in 44 actions. V84h
lifts search to `(anchor,color)` and compiles this waypoint structure with a
4,096-expansion bound.

Frozen v84h candidate `candidate-ff5318e279917649`, from source commit
`906af49`, passed that behavioral gate once. It reached `re86` 4/8 at
`[24,36,56,44,240,0,0,0]`, target score 27.7777777778. Level 4 consumed
exactly the predicted 44 actions. The immutable report is
`reports/experimental-v84h-paint-re86-r1-400.json`, SHA-256
`20948ea86de811784a896085e831fd98cc83983288f6044b5a5093c1a3484ab6`.
Level 5 is now the concrete falsifier. At the end of the budget its factor and
reference parsers abstained as `not-grounded`, so the next step is to inspect
its initial relational object and seek a composition of existing translation,
focus, factorization, reference, and paint morphisms before adding vocabulary.

That inspection found a unique compositional account. Three movers cover ten
landmarks: X and plus jointly realize the six color-9 constraints and must
both be painted 9; diamond realizes four color-8 constraints and must be
painted 8. The plus initially overwrites two of those color-8 centers, making
their rendered color 12. Treating only causally explained center overwrites as
latent variables yields one minimum-cost exact cover: X `(30,15)`, plus
`(33,51)`, diamond `(51,36)`. Bounded paint-aware routes plus two focus
transfers solved level 5 through the public wrapper in 63 actions. Implement
this as a joint latent-color placement CSP, not a watched route, and require
the autonomous agent to reproduce the 63-action consequence.

V84i's first frozen run grounded the unique three-option CSP with zero
constellation conflicts but remained 4/8. Its trace localized the failure:
after seven plus-route steps, the lower-priority paired-object advisor
interleaved five actions before the option resumed. The executed 63
constellation selections were therefore not the 63-action program. The next
offspring enforces standard hierarchical-RL option atomicity: once a bounded
reference option is committed, lower-level advisors cannot interrupt it before
termination or an unavailable-action failure.

V84j passed the autonomous gate. Frozen candidate
`candidate-fd6a1798e5f36721` reached 5/8 at
`[24,36,56,44,63,177,0,0]`, target score 41.6666666667. Level 5 matched the
black-box prediction exactly at 63 actions. Report
`reports/experimental-v84j-committed-composite-re86-r1-400.json`, SHA-256
`90a5b9ed938a63e63ff7004b26969b28b419cf39d6b7e6c834ee3cb387c4a24a`.
Level 6 is now the concrete falsifier.

Black-box interventions identify level 6 as a product configuration-space
problem. The plus is two conserved 25-pixel segments; the shared translation
acts diagonally on their product, while the neutral obstacle can block one
factor and thereby create the target relative offset `(-9,+9)`. The square is
a 72-pixel loop whose target 10×28 perimeter also has length 72; pushing it
around the same obstacle changes width and height while conserving perimeter.
A geometry-derived 57-action program solved the level. Implement a bounded
factor/obstacle option compiler and require autonomous reproduction; do not
retain the watched action string.

V84k passed that gate once. Frozen candidate `candidate-93770ad218d4a821`
reached 6/8 at `[24,36,56,44,63,57,120,0]`, target score
58.3333333333; level 6 matched the predicted 57 actions exactly. Report
`reports/experimental-v84k-deformable-re86-r1-400.json`, SHA-256
`3655b3e259cde1f2f2ee8d50b19c5344d49042bccef884939617fe75b0ac4f71`.
Level 7 is now the concrete falsifier. Because the first six levels consume
280 actions, levels 7–8 must jointly fit the remaining 120-action budget to
cross 20 from this game alone.

Controlled level-7 translations have now identified its compositional
objects. A 19×19 cross and a 37×19 cross factor into four conserved line
segments. A proposed cross-object reassignment is unreachable and therefore
rejected. The minimal reachable binding preserves the two bundles: the 37×19
cross shears to color 8, the 19×19 cross shears to color 11, and a 13×13
perimeter loop independently targets opposite color-9 corners of a 19×7
rectangle, preserving perimeter 48. Next compile a bounded joint
factor-separation/paint/exact-cover option, validate its route through the
public wrapper, and reject it if factor-level paint or obstacle effects do not
commute as predicted.

Public-wrapper validation supplies a 32-action color-9 loop option. Fully
continuous factor-span checks reject the apparent 45-action small-cross and
34/36-action asymmetric-cross shortcuts: same-color target centers were still
visible but unoccupied. The trustworthy baselines are 56 actions for the
small color-11 cross and 50 actions for the color-8 asymmetric cross. Search
for compression using exact span occupancy and require an actual level
transition; only then implement the generalized compiler rather than
retaining observed strings.

The trustworthy 56 + 32 + 50 action options plus two focus transfers completed
level 7 through the public wrapper at total action 420. This extended-horizon
diagnostic validates the full construction but is not a candidate result.
Compress at least 40 actions across these options or the six-level prefix,
using exact factor spans and the actual level transition as the terminal
predicate. Then implement and test only the invariant-derived compiler.

That compression gate is now met diagnostically. The exact routes are 38,
30, and 50 actions, plus two focus transfers: 120 actions total. The public
wrapper transitioned to level 7 at total action 400. Implement a conservative
factor-bundle compiler whose waypoints and counts are derived from lattice
step, obstacle bounds, palette fibers, segment spans, loop perimeter, target
extrema, and focus cycle. Freeze and run it autonomously; do not embed the
watched action sequence.

V84l passed that autonomous gate once. Frozen
`candidate-5f09e48c374d0a52` reproduced the exact 120-action level-7
composition and reached 7/8 at `[24,36,56,44,63,57,120,0]`, score
77.7777777778. Report
`reports/experimental-v84l-factor-bundle-re86-r1-400.json`, SHA-256
`438623478f7e156b806ba606b4450659cb1ebd6012fcc18c5372a7f2dba53689`.
The projected aggregate is 19.4665592092, leaving 0.5334407908. Repeat v84l,
then seek the smallest independently verified gain that crosses 20; do not
submit a projection.

The second fresh-process v84l run exactly reproduced the first. Report
`reports/experimental-v84l-factor-bundle-re86-r2-400.json`, SHA-256
`d590a183d2510acfcca9ac427bf1a9f7985a13ade408b598ae82c60f30832c9d`.
Treat the seven-level gain as deterministic and move to the minimum remaining
cross-game score opportunity before the full preservation gate.

That opportunity is `tr87` level 5. A frozen-v84l control exactly preserved
v82f at 4/6, `[56,45,44,38,217,0]`, score 47.6190476190. Its fifth panel
reverses the established analogy interface: the editable alternating-color
rows carry group boundaries, while two fixed five-glyph rows supply the target
classes. The editable run pairs have lengths
`(1→1),(1→2),(2→1),(1→1)`, whose source and answer totals each equal five.
Sequentially transporting the fixed rows through this unique partition yields
eight group goals. A derived 19-action public-wrapper program completed the
level at total action 202.

The v84m hypothesis is a conservative grouped-dihedral functor. It recognizes
only equal-size framed glyphs, exactly two endpoint colors, alternating mixed
runs above compatible fixed rows, equal partition totals, and one uniquely
marked editable group. It maps each fixed glyph to its dihedral equivalence
class, transports those classes through the run partition, and reuses only
causally retained selector/mutation controls. Malformed partitions and
ambiguous selectors abstain. The real held-out frame grounds uniquely as group
lengths `[1,1,1,2,2,1,1,1]` with seven unsatisfied groups; synthetic positive
and negative controls and static checks pass.

V84m passed the first autonomous target run. Frozen
`candidate-07d24ee8acf946c9` reached `tr87` 5/6 at
`[56,45,44,38,55,162]`, score 71.4285714286. Level 5 took 55 actions, below
the preregistered 66-action cap. Report
`reports/experimental-v84m-grouped-tr87-r1-400.json`, SHA-256
`792ba1d27c432e8c7c704afed86a6db9e42cecbeb572a8982bd3c31ea9499674`.
With v84l's measured `re86` gain, the unchanged-suite projection is
20.4189401616. Repeat in a fresh process before the full suite.

The second fresh-process target run exactly reproduced
`[56,45,44,38,55,162]` and score 71.4285714286. Report
`reports/experimental-v84m-grouped-tr87-r2-400.json`, SHA-256
`3fdc513156c80b8a1d1437b3f173fd97cd64bbe21271e931228850528a004bb3`.
The target-repeat gate passes. Run the full 25-game process-isolated suite and
compare every non-target vector with v82f before promotion.

That gate now passes. The complete v84m suite scored
**20.418940161588477 / 100**, solved 47/183 levels across 14 games, and fully
completed 3/25 games. `re86` and `tr87` changed exactly as predicted; all 23
other score, level, and action vectors exactly match v82f. Report
`reports/official-isolated-v84m-grouped-dihedral-400.json`, SHA-256
`4823d8a358e7798293887ec8eaafd96041b4a5655f7b4da9154b7a7894bfc7c7`.
The quality and export gates pass: 461 tests passed with 3 skips, Ruff and
mypy are clean, both network-disabled smoke paths pass, and the technical
prize audit passes. Exact artifact SHA-256 values are:

- candidate:
  `b32d3b48f358951abf22a375faab92b0a6ea705aa1721f1b3d9ecc2098f85e54`;
- overlay:
  `7e4ddf76c500396b7dc711977677d7aeeac068e354058124dbbbf390346d2e19`;
- notebook:
  `875cc88012b24008103017e98d64c6e49e9ae496c371da9c0eb4bbcefa290064`.

V84m is accepted locally. Submit the exact notebook through Kaggle and record
its notebook version and submission ID separately from the local score.

The exact private v84m notebook version 1 completed and emitted
`submission.parquet`. Kaggle rejected the subsequent code-submission request
with HTTP 400. The live ledger shows why: v74 submission `55123277` already
consumed the 2026-07-31 UTC daily allowance and remains pending. Retry v84m
only after the daily quota resets; do not alter or re-export the completed
version. V65b submission `55113224` has completed at public score 0.02.

Required gates are:

1. submit completed v84m notebook version 1 after the daily quota resets;
2. record notebook version, submission ID, and pending/terminal state;
3. keep local, Kaggle public, and Kaggle private scores separate.

## Rejected experiment: v85 compressed progress-path transport

The immutable v84m cognitive audit contains 43 observed progress events and 75
failure/reset events across all 25 games. Generic exploration owns every
failure: 40 immediately follow hierarchical action-family selection and 35
follow untried-state selection. Four repeated hierarchical selections precede
39 failures; four repeated untried selections precede 34. The source report is
`reports/v84m-progress-failure-signatures-v1.json`, SHA-256
`c5dd2d22b0fc21ac5652be900745da835ff23e09a39f4f1923aa5c1bd07b9614`.

V85 tests one hypothesis only: a shortest successful state-graph path can be
compressed into grounded action roles and transported as a bounded
hierarchical option to the next level. The mechanism:

1. searches only observed non-reset edges within the completed level;
2. requires a grounding for every edge;
3. run-length encodes consecutive equal roles;
4. rebinds roles prospectively in the next level;
5. explores ambiguous equal-score bindings deterministically;
6. stops after 64 selections and abstains when no role matches.

This is internal retrospective credit, not a retained public route: no game
ID, frame, fixed coordinate, or offline replay enters the candidate. First run
partially solved games plus complete preservation sentinels. Reject on any
accepted score/action regression. Do not combine failure avoidance with this
offspring; that remains a distinct causal hypothesis.

The 14-game isolated gate rejected v85. It added no completed level, reduced
the gate mean from **36.4623931457** to **35.9812800045**, and regressed
`ft09` from `[4,7,14,16,94,27]` to `[4,7,14,16,250,26]`. The mechanism was
not inert: `ft09`, `lf52`, `lp85`, and `tn36` reached the 64-selection cap.
`lp85` improved locally to 41.8310410985 and `tr87` changed its action vector
at equal score, but neither compensates for an accepted regression. Immutable
report `reports/experimental-v85-progress-path-targeted-r1-400.json`,
SHA-256
`be3f766396ef938ad7bb724078283ad32c806a255220cf1ce893a21bd8a3366f`.
Keep `enable_shortest_progress_path_reuse` exact-off.

## Next experiment: terminal-edge viability credit

The audit's strongest independent signal remains the 75 failures owned by
generic exploration. Test a bounded, prospective failure model rather than
another successful-route replay:

1. observe terminal predecessor/action transitions without changing policy;
2. quotient only by an existing nuisance-normalized structural state and a
   grounded action role;
3. require the same abstract terminal edge in at least two distinct concrete
   predecessor states before it gains avoidance authority;
4. retire or scope authority at level change and cap retained evidence;
5. use the model only to reject an otherwise generic exploration proposal,
   never to preempt a grounded specialist option;
6. validate exact-off preservation and synthetic alias/contradiction controls
   before a real-game gate.

The hypothesis is falsified if the abstraction aliases safe and terminal
edges, fails to activate on repeated-death games, or regresses any accepted
completion. It targets viability, not goal inference, so reduced failures
without progress are diagnostic evidence rather than a promotion.

The exact-off integration and synthetic falsifier now pass. Frozen v86
candidate `candidate-11e6748f184d5586`, inference fingerprint
`613927c833304db2c92cc8e7e8d1c3b7c54f608ac6c2d3a905aa82995226d79d`,
changes one config bit. One terminal transition only proposes an edge; an
exactly repeated concrete predecessor cannot confirm it; a second concretely
distinct but color/global-translation-equivalent source can; and a safe
counterexample quarantines it. The filter is evaluated only after all grounded
specialists abstain. The next gate is a repeated-death game set with cognitive
telemetry; require real prospective confirmations before interpreting any
behavior change.

That gate is complete and v86 is inert. All 16 failure-game score/action
vectors exactly match v84m. Across 75 terminal observations, it proposed 65
whole-scene/role hypotheses but produced zero predictions, confirmations, or
filtered choices; two safe counterexamples were recorded. Report
`reports/experimental-v86-terminal-viability-failure-r1-400.json`, SHA-256
`f695a05a5d7907a32e9d86f1d4f29429959e204e78c113db4e4f71eecfb5533d`.

The corrected game-local quotient audit finds no clean action-only edge.
Grounded action roles do expose five clean prospective confirmations across
`bp35`, `s5i5`, `sp80`, and `vc33`, each arising from object-bound clicks, plus
five post-authority uses. Whole-scene structural keys erase this recurrence by
including irrelevant relational layout. Audit
`reports/v84m-terminal-viability-quotients-v1.json`, SHA-256
`dbd8272a05239bf8d11727f9f82e4e5321f15852e133742aea4f57acfe1e08e7`.

Next freeze a separate role-only v87 mode. Keep the requirements of two
distinct concrete terminal predecessors, same-level scope, safe-counterexample
quarantine, hard evidence caps, and specialist priority. Gate first on the four
games above plus aliasing sentinels `cn04`, `su15`, and `tu93`. Reject if no
filter activates, any accepted vector regresses, or a safe role gains
authority.

Frozen v87 candidate `candidate-6e6ed3468326662e`, inference fingerprint
`c0773e76e5f82944c40cdb9170a4c569de2fe60838d566c2377973e2969d5ad6`,
implements that one additional mode bit. The concrete-frame hashes remain
evidence identities only; the retained forbidden assignment is the grounded
role. Synthetic tests require two distinct frames, separate different roles,
and preserve safe-counterexample quarantine.

The seven-game online gate rejects v87 for task promotion. It earned four
prospective confirmations and filtered seven token opportunities. Concrete
behavior changed on `s5i5` and `vc33`, but every score, level-action vector,
and failure count exactly matched v84m; `bp35` filtered a nonselected token.
Report `reports/experimental-v87-role-viability-targeted-r1-400.json`,
SHA-256
`68c0d3837d9acdd09b06043e2f65d38c5e8b9b674e3551aeb15f1ac848ab56ab`.
Keep both viability modes exact-off in accepted candidates.

Do not broaden the taboo or lower its evidence threshold. The next hypothesis
must add direction: construct a bounded abstract causal graph whose nodes are
compressed effect/state roles, attach terminal roles as forbidden constraints,
and learn a positive potential only from progress or prospectively confirmed
subgoals. A useful formulation is a finite MDP homomorphism/quotient functor:
concrete transitions may merge only when their available grounded-role effects
and observed outcomes commute. Plan over the quotient with a CSP/CEGIS
version space of candidate subgoals. First validate bisimulation and aliasing
offline; then test one partially solved game and one zero-progress game.

The offline partial-bisimulation audit now supports that substrate. Across all
9,160 accepted v84m transitions it found 458 prospective donor-only
role-effect predictions: 422 confirmed and 36 conflicted, for **92.14%**
precision. It exposed 18,901 locally untried roles with donor predictions.
Every hypothesis remained game-local; a compatible pair required at least one
shared deterministic role-effect and no overlapping contradiction. Report
`reports/v84m-partial-bisimulation-audit-v1.json`, SHA-256
`42efa51c9f2fe41a0ab4e044c4e4820e4b68716d97f9caa6f71d19e4e5049c34`.

Frozen trace-only v88 candidate `candidate-de408a819b3f6dcd`, inference
fingerprint
`8cb07f524cf875937c985a5dceb80b2ae0020dec560d6199638d884ecc6c4852`,
implements the bounded online version without changing selection. It resets at
level boundaries, retains evidence across same-level retries, caps states,
roles, and outcomes, predicts before integrating each row, and records
confirmations, conflicts, ambiguity, and cap failure. First measure exact
runtime precision and preservation on high-opportunity games; do not activate
abstract-frontier control until that trace gate passes.

That trace gate passes. Across `g50t`, `lp85`, `ls20`, `sc25`, `sk48`,
`sp80`, `su15`, and `tu93`, v88 exactly reproduced every v84m score,
completed-level action vector, failure count, and action total. The online
quotient recorded 3,163 observations, 308 prospective predictions, 285
confirmations, and 23 conflicts, or **92.53% precision**; `ls20` was 42/42
and no cap failed. Report
`reports/experimental-v88-bisim-trace-r1-400.json`, SHA-256
`49f4db4efb7dd71a033caf0ac4edc49cf208612bfa18d91e424cb9cdd542025b`.

Freeze v88 as the trace control and build one minimal operative child. Its
abstract-causal-frontier advisor must remain below every specialist, require
at least eight flawless current-level prospective predictions, disable itself
for the level after any conflict, select only a locally untried role with a
unique predicted positive effect, and stop after 32 selections. First gate on
the same eight games. Reject any accepted-vector regression; promote to a
broader gate only for a level gain or a material deterministic efficiency
gain.

Frozen operative v89 candidate `candidate-bfeac7aef52e2878`, inference
fingerprint
`8ead5910fee846f1a6d6b337528b6fc0d2502a9d517b0bcce6fc38223bbe39a5`,
implements exactly that single additional advisor. Its parent is trace-only
v88, so an exact v88 comparison isolates selection from representation.

The eight-game gate rejects v89. It made 22 causal-frontier selections across
five games and changed `ls20`'s action distribution, but every score, level
count, completed-level action vector, and total action count exactly matched
v88. V89 recorded 285 confirmations from 309 predictions and 24 conflicts;
the changed `ls20` sequence introduced a conflict absent from v88. Report
`reports/experimental-v89-abstract-causal-frontier-r1-400.json`, SHA-256
`a8c55547d17ad70937c942b7577cfbe11fcbc6431a960ac5559af16f6b923154`.
Keep the control bit exact-off and retain v88 only as a trace substrate.

Do not retry generic “positive effect” ordering. The next bounded audit should
compare two uses of the quotient: (a) CEGIS-style selection of an untried role
whose compatible donors predict different outcomes, measuring version-space
elimination; and (b) progress-backed abstract potential learned only from
completed trajectories. Implement control only if the offline chronological
audit shows that the proposed signal predicts information gain or progress
better than v84m's generic novelty rank.

That audit chooses CEGIS and rejects transported progress distance. Across the
accepted chronological streams, 878 states expose 1,672 ambiguous frontier
roles. All 135 such roles actually executed eliminate hypotheses, removing
797/2,005 compatible donor models (39.75%); 129 occur under generic
exploration. The progress control finds 187 unique cross-level predicted-best
states, but v84m chooses the role only 14 times, and only 1/24 near-progress
opportunities uses it. Report
`reports/v84m-causal-version-space-audit-v1.json`, SHA-256
`49bc11b138ee46b43dcb09a18140afa00cd74131fc3b8677ae4d823d8b4a03d7`.

Implement one v90 sibling of trace-only v88, not a descendant of rejected
v89. Its lower-priority CEGIS advisor may select only a locally untried legal
role with at least two donor outcome hypotheses, ranks by expected hypothesis
elimination, records the eliminated version-space mass after observation, and
has a hard per-level query cap. It must not reuse transported progress
distance or label any outcome as reward. Gate first on high-opportunity
`ar25`, `g50t`, `sc25`, `sk48`, `tu93`, and `wa30`, with `lp85` and `sp80`
as preservation sentinels.

Frozen v90 candidate `candidate-915572415e361c0c`, inference fingerprint
`6968d3c650c6d3ae1534f820335787c0ed359431623a82623d0935ebd019718e`,
is that v88 sibling. It requires four current-level confirmations at at least
75% prospective precision, caps queries at 16 per level, and records both
represented and eliminated donor hypotheses.

The eight-game gate validates v90's causal attribution but withholds task
promotion. It selected 80 queries, represented 470 compatible donor
hypotheses, and eliminated 217 (46.17%). Action distributions changed on four
games; every score, level count, completed-level action vector, and total
action count exactly matched v84m. Report
`reports/experimental-v90-causal-discrimination-r1-400.json`, SHA-256
`9a8b2a967f8d9142f96d7a3b4689fcdd1b0ef961019126d7dc7194eff4ef8fa2`.
Keep v90 exact-off in accepted candidates.

The next child should consume the learned compression, not collect more
information for its own sake. Audit and implement bounded abstract
intervention coverage: after specialists abstain and the quotient is
predictively mature, deprioritize only locally untried roles whose unique
outcome is supported by at least two compatible donor states. Preserve
ambiguous roles, unsupported roles, locally observed roles needed for
navigation, and exact fallback when every legal role is redundant. Reject any
accepted-vector regression; measure whether the saved redundant tests increase
distinct abstract frontier coverage or task progress.

Frozen v91 candidate `candidate-3011d26c13f51690`, inference fingerprint
`8a9946dfba2aee6e180d6b47c471919788e1e89f8f5f149b5cd0dd6f7070acf8`,
is a v88 sibling that implements only this compression. It needs the same
four-confirmation/75%-precision maturity gate, requires two donor supports,
caps filtering at 64 generic decisions per level, and falls back when every
legal role is redundant.

Reject v91 for task promotion. It filtered 7,201 concrete tokens over 368
generic decisions and expanded raw-state coverage on `g50t`, `ls20`, and
`tu93`, but every eight-game score and level-action vector exactly matched
v88. Report `reports/experimental-v91-bisimulation-coverage-r1-400.json`,
SHA-256
`80d6ae92b850b0a7cc1ea73ae2307410167fc66130a158280f38559dbe32dc8d`.
Keep the bit exact-off.

Stop mutating undirected exploration. The quotient has now validated
prediction, CEGIS refinement, and intervention compression without progress.
Return to hierarchical goal induction: audit progress and terminal-adjacent
states for relational predicates conserved across structurally different
games, retain competing predicates as a bounded CSP version space, and test
actions by whether their evidenced effects reduce a selected predicate's
violation count. Require the predicate to distinguish progress from failure
and no-op before it can define a subgoal option.

The first target diagnosis validates exactly such a predicate. A black-box
19-action `ls20` level-1 solve factors into:

1. learn a four-generator translation action on a rigid multicolor 5×5 body;
2. plan on its free-anchor graph to a small relational operator;
3. observe the operator-induced transition of a coarse 3×3 display;
4. compare that display to a separate invariant goal glyph;
5. plan through the terminal corridor only after display equality.

Report `reports/ls20-black-box-phase-topology-v1.json`, SHA-256
`96d5b13bee6b50c659f19dccc5bfccdd925d6ce1effc01a757cb357946777efd`.
V92 implements the general bounded substrate without encoding those
coordinates, actions, colors, or game ID. Frozen candidate
`candidate-42dbfa39cba78041`, source commit `e03fb30`, and inference
fingerprint
`32462ddff38fa9ba86691e66601adcef93a9147e0b02e5f219433435f9f54c1f`
compile observed rigid translations, scale-normalized embedded displays, and
operator-induced display transitions into bounded options over
`anchor × phase`.

The causal target passes twice. Both isolated `ls20` runs advance level 1 in
exactly `[17,383,0,0,0,0,0]`, versus v84m's
`[400,0,0,0,0,0,0]`. The accepted-win preservation gate then exactly
reproduces every score, completion flag, action total, and completed-level
action vector on all 14 previously positive v84m games; only `ls20` changes.
Report `reports/experimental-v92-accepted-win-preservation-r1-400.json`,
SHA-256
`3e5ecefb295342a18f883da0ee30fc07bd1c3012f592739ab81fbc16d4790b84`.

That complete gate passes. The 25-game score is
**20.561797304445623/100**, with 48/183 levels across 15 games, 3 complete
games, and 9,185 actions. Only `ls20` changes from v84m; all 24 non-target
vectors are exact. Report
`reports/official-isolated-v92-phase-topology-400.json`, SHA-256
`0caf5a52474ac7f89703861fa81b52528b45f4f806ba623d689362fb852d4f9a`.
The quality gate passes with 493 tests and 3 skips, Ruff and mypy are clean,
and exact export plus network-disabled smoke pass. V92 is accepted.

Submit the exact v92 notebook subject to Kaggle's daily quota. Then diagnose
`ls20` level 2 from the post-progress public observation without weakening the
accepted initiation set. The next accommodation should support a bounded
version space of multiple operators or phase cycles only if each transition
is prospectively confirmed; preserve v92 as the new exact-off control.

The exact v92 notebook `pauloabelha/reflector-arc-agi-3-v92` version 1
completed and emitted `submission.parquet`; the competition request returned
HTTP 400 while v74 submission `55123277` still occupied the UTC daily
allowance. Retry that exact version after quota reset.

V93 `candidate-d362ccca5fe08c64` tests the first level-2 accommodation. It
preserves a plain translation when operator contact instead produces a
same-body teleport, directly replans on the rewritten topology, rearms
entry-triggered display transitions, and latches equality across a contextual
reset. The official target remains exactly 1/7 at
`[17,383,0,0,0,0,0]`; 109 planner decisions observed two contextual
transitions but did not advance level 2. Report
`reports/experimental-v93-contextual-phase-ls20-r1-400.json`, SHA-256
`6e4cad2dae2c86d228976ced77c526099ed2d6fb279bffc783844e62b2b9f7a9`.
Reject v93 without a preservation suite.

The next level-2 experiment must retain a bounded terminal-predicate version
space. Display equality is causal evidence for a topology transition, not
proof that the display host is enterable. Candidate predicates should include
reachable boundary contact, newly enabled regions, and distinctive relational
markers; eliminate a predicate on a prospectively observed blocked edge
instead of converting it directly into a committed terminal option.

The subsequent public-wrapper diagnosis falsifies the topology premise more
precisely. The large same-color strip loses four cells on every action and is
restored from zero to 84 on a reset. The apparent contextual teleport is a
21-action horizon reset, and its coincidence with operator contact confounded
v93's causal attribution. The two hollow same-color spatial components are
consumable resources: contact restores that budget indicator to 84.

A composed legal plan advances level 2 in 45 actions:

1. reach the operator and induce the first normalized phase;
2. use the nearby resource just before the horizon becomes binding;
3. return to induce the second phase;
4. rearm/reenter once to reach display equality;
5. use the remaining distant resource only now, resetting the horizon;
6. enter the fixed display host and advance.

Report `reports/ls20-black-box-temporal-resource-v1.json`, SHA-256
`e0d486ae7986b2f1c2ab227b39bcb44b73a23bf7e44fb007638b28001b222f4d`.
The next offspring must implement this as a generic bounded
resource-constrained option CSP, not as a route. It should infer a monotone
budget component, its action cost, same-role resource candidates, causal reset
evidence, option distances, and phase equality. Receding-horizon selection
should apply an operator only when a resource or terminal remains feasible
afterward; otherwise it should delay the resource reset to maximize useful
future budget. Context resets must be treated as exogenous temporal
boundaries, never as evidence that a terminal predicate has become true.

V94 implements that product state and passes transformed synthetic tests. On
the verified level-2 recording, it acquires authority only after all four
plain translations are evidenced and then matches the final 26/26 actions,
including two observed budget resets and three phase applications. The first
fresh-process target run does not advance: candidate
`candidate-c3ea3fa6d77e2ef2` remains 1/7 at `[17,383,0,0,0,0,0]` in
`reports/experimental-v94-temporal-resource-ls20-r1-400.json`.

That negative run localizes the next accommodation. During the second retry,
the planner grounds the 21-step meter, selects a reset route, reaches phase
equality, and still expires because the selected reset option is reconsidered
and abandoned on the following step. V94b therefore changes no role detector,
cost model, or route: it adds standard option atomicity. An active reset target
must remain authoritative until its predicted reset occurs, its role
disappears, or its bounded path is falsified. Evaluate v94b on `ls20`; only a
second-level gain warrants repeat and preservation gates.

The first source-frozen v94b run passes that target gate. Candidate
`candidate-2d9cadd5859ce47d` at source `203fa2e` reaches 2/7 with
`[17,240,143,0,0,0,0]`, improving the accepted parent by one level and
finishing level 2 after 240 actions across bounded retries. Report
`reports/experimental-v94b-atomic-resource-ls20-r1-400.json`, SHA-256
`04f73bcb95e5849e2afc6662802b809a5bc1593cf60a7fe9713d53916253e50a`.
Next run an exact target repeat. If it reproduces 2/7, run the accepted-win
preservation suite against v92, followed by all 25 games, full quality gates,
and exact Kaggle export.

The second fresh-process run is exact: 2/7, four resets, score
`5.983258928571429`, and `[17,240,143,0,0,0,0]` again. Report
`reports/experimental-v94b-atomic-resource-ls20-r2-400.json`, SHA-256
`0e9e497302dabb9ea6cb8a8024925e07b75c1b10941a420e345842e7af038f4c`.
The target-repeat gate passes; run accepted-win preservation now.

The accepted-win gate passes: 49 levels, 5,185 actions, and score
`34.43045086455222`, with only `ls20` differing from v92. All fourteen
non-target vectors are exact. Report
`reports/experimental-v94b-accepted-win-preservation-r1-400.json`, SHA-256
`d833d7912755edb632e66cfbb8494d424d0434dd8ed6e8b5996731397ed7644e`.
Run all 25 public-development games from fresh processes next.

The complete run passes with 25/25 coverage: score
`20.65827051873133`, 49/183 levels, 15 games with progress, 3 complete games,
and 9,185 actions. Only `ls20` differs from v92. Report
`reports/official-isolated-v94b-atomic-temporal-resource-400.json`, SHA-256
`8e75171f64ad6879ba1f9298fa32fa66a5b714772382b7baf1c8b77956d97c6e`.
Run the full tests, Ruff, mypy, exact export, offline package smoke, and prize
audit. If all pass, promote v94b and build the exact Kaggle notebook.

All final gates pass: 498 tests with 3 skips, repository-wide Ruff, mypy over
90 source files, exact candidate export, both network-disabled smoke paths,
and `TECHNICAL_READY=true`. V94b is accepted. Its exact candidate/overlay/
notebook SHA-256 values are
`0432087230ed083c9410fa94de367c38a536bcb4c565f8f7b160992bad3f28d5`,
`f676d8294f49cfa8c0152aa524021c6175ee10c4f51093d09b95e8208c40d047`,
and
`585518a9acb9ee1cc7d612b14dbfdaeb9d2279f1149463aaa55dbd37e5342219`.
Freeze the documentation/report commit, push the exact v94b notebook, and
attempt a competition submission only if Kaggle's daily quota permits.

The exact private notebook `pauloabelha/reflector-arc-agi-3-v94b` version 1
completed and its output was downloaded as `submission.parquet`. The requested
competition submission attempt returned HTTP 400; a read-back shows no new
submission ID, with v74 `55123277` still pending as today's submission. Retry
the already completed v94b version 1 after the UTC quota reset; do not rebuild
or change the accepted artifact.

V83's one-dimensional track replay is rejected: it was active on `sc25` but
remained 0/6 in 400 actions because geometric endpoint proximity was not the
task goal.

## Accepted parent mechanism: v25 global relation constraints

Candidate: `candidate-036a55bfb6956008`

File: `candidates/v25-global-relation-constraints-400.json`

Hypothesis:

- Infer one coordinate-free tile lattice from observations.
- Coordinate overlapping clue constraints on that lattice and act only where
  all observed constraints agree that a block violates the learned relation.

Current evidence:

- Two official `ft09` runs exactly matched: five levels with level action
  counts `[4, 7, 14, 16, 94]`.
- The four-game gate preserved all accepted v21 completions and reached eight
  levels total.
- Every runtime action can now emit a bounded cognitive JSONL event containing
  advisor arbitration, transition evidence, and construction deltas. The LLM
  may inspect these traces between runs but is never called by the deployed
  policy.
- Full verification passes: 124 tests (3 skipped), Ruff, mypy, both packaged
  smoke paths, and exact-v25 export.
- Two paired process-isolated gates exactly reproduced: the source-matched
  ablation reached seven levels and v25 reached eight, preserving all prior
  completions.
- The strict isolated 25-game run scored 2.9104325118/100 with 8/183 levels
  and complete coverage. Its one-factor ablation scored 2.1693300953 with
  7/183. V25 is accepted.

## Accepted experiment: v29 mature-stall causal role reuse

Candidate: `candidate-309548c858c10616`

File: `candidates/v29-mature-causal-role-reuse-400.json`

Mechanism:

- after 32 interventions without level progress, reuse only roles with an
  observed rendered response;
- cap reuse at eight trials per level, then return to variation;
- suppress the advisor when a conserved learned relation is active.

Evidence:

- the watched five-game curriculum exposed that unbounded reuse solved
  `lp85` but regressed `ft09`;
- two exact six-game runs preserved all affected accepted action counts and
  added `lp85` L1 in 37 actions;
- the full source-matched v25 genome reproduced 8/183 and
  `2.9104325118287466/100`;
- the full v29 candidate preserved those eight levels exactly, added `lp85`,
  and reached 9/183 and `2.9338884001495003/100`;
- 148 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, and the exact genome exported without translation.

V29 is accepted.

## Accepted experiment: v30 marker-relative cyclic transport

Candidate: `candidate-2fabaa20cd4cd160`

File: `candidates/v30-marker-relative-cyclic-transport-400.json`

Mechanism:

- detect appearance-relative anchors through four symmetric corner markers;
- infer controller effects only from conserved exact cyclic shifts;
- construct the marker-match goal only when an evidenced shift predicts level
  progress;
- factor overlapping tracks and search their composed effects with bounded
  expansions and advisor trials.

Evidence:

- three isolated `lp85` observations, including two permanent scorecards,
  reproduced level actions `[37, 8, 355]`;
- the five-game gate preserved every accepted v29 action count and increased
  the total from nine to ten levels;
- the exact-off full source control reproduced v29 at
  `2.9338884001495003/100` and 9/183;
- the full v30 candidate reached 10/183 and
  `3.1894439557050553/100` with 25/25 coverage;
- 153 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, and the exact genome exported without translation.

V30 is accepted.

## Accepted experiment: v31 grounded graph-cycle transport

Candidate: `candidate-98a22d6f908c6eb7`

File: `candidates/v31-grounded-graph-cycle-transport-400.json`

Mechanism:

- enumerate only bounded, chordless cycles around already marked anchors;
- bind a controller only after an exact conserved one-step token rotation;
- retain grounded episode-local permutations and their shared slots;
- compose at most 24 interventions toward the v30 marker-match goal.

Evidence:

- independent `lp85` runs reproduced `[37, 8, 54, 301]`;
- the bounded full candidate preserved all ten v30 levels exactly and added
  `lp85` level 3;
- the exact-off full source control reproduced v30 at
  `3.1894439557050553/100` and 10/183;
- the full v31 candidate reached 11/183 and
  `3.2992976365463904/100` with 25/25 coverage;
- the unbounded six-worker attempt was terminated without a score and caused
  an explicit node/degree/expansion/frontier repair before promotion;
- 155 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, and the exact genome exported without translation.

V31 is accepted.

## Accepted experiment: v32 parameterized select/apply/commit

Candidate: `candidate-e9c00d0968c2832a`

File: `candidates/v32-parameterized-select-apply-commit-400.json`

Mechanism:

- detect an ordered reference row with distinct attributes;
- require an unordered selector row with the exact same attribute set;
- bind each reference attribute to its selector and corresponding neutral slot;
- execute the bounded select/apply pairs, then test the first unused non-click
  control as a commit hypothesis.

Evidence:

- two independent `sb26` target runs solved level 1 in nine actions;
- the current-source exact-off target control remained at 0/8 after 400
  actions;
- the six-game gate preserved all eleven v31 completions at exact action
  counts and added `sb26`;
- the full current-source exact-off control reproduced v31 at
  `3.2992976365463904/100` and 11/183;
- the full v32 candidate reached 12/183 across six games and
  `3.4104087476575016/100` with 25/25 coverage;
- 158 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, and the exact genome exported without translation.

V32 is accepted.

## Rejected experiment: v33 multiline target accommodation

Parent: v32 `candidate-e9c00d0968c2832a`

Observed disequilibrium:

- v32 reaches `sb26` level 2 in nine actions, then exhausts the remaining 391;
- level 2 retains an ordered row of seven distinct reference attributes and an
  unordered selector row with the exact same attribute set;
- the seven identical neutral targets are partitioned into two intervening
  rows of three and four, so v32's single-row cardinality test rejects them.

Preregistered mutation:

- preserve v32's exact reference/selector bijection;
- when no single neutral row has the required cardinality, merge only
  identical-color, identical-shape neutral targets between the reference and
  selector rows;
- require two or more target rows, exact total cardinality, and bounded size;
- bind the ordered reference attributes to targets in deterministic visual
  reading order, then use the already bounded commit hypothesis.

Falsifier:

- the advisor stays silent without an exact reference/selector attribute
  bijection and exact neutral-target cardinality;
- the mutation is rejected if it does not reproduce `sb26` level 1 and advance
  level 2 in the predicted 15 additional actions, or if any accepted
  completion regresses.

Result:

- v33 reproduced `sb26` level 1 in nine actions;
- it executed the preregistered 15-action row-major program on level 2;
- level 2 did not advance, and the final result remained `[9, 391]`;
- therefore multi-row cardinality was real, but ordinary reading order was the
  wrong binding relation. V33 is rejected without a preservation or full gate.

## Rejected experiment: v34 bounded spatial-order variation

Parent: accepted v32 `candidate-e9c00d0968c2832a`

Hypothesis:

- when an earned attribute-binding scheme finds an exact multi-row target
  layout but lacks evidence for target order, treat order as a symbolic
  parameter rather than committing permanently to row-major order;
- construct at most four coordinate-free order hypotheses: row-major,
  row-boustrophedon, column-major, and column-boustrophedon;
- test each complete binding program, use the remaining non-click control as a
  clear hypothesis between failed programs, and stop automatically on level
  progress.

Falsifier:

- the advisor remains silent without v32's exact attribute bijection and
  v33's exact multi-row neutral-target cardinality;
- the variation family is rejected if none of its four bounded programs
  advances `sb26` level 2, or if it regresses an accepted completion.

Result:

- the frozen candidate reproduced level 1 in nine actions;
- it executed all four preregistered traversal programs, separated by the
  bounded clear hypothesis, but level 2 did not advance;
- the isolated result remained one level and `[9, 391]`;
- therefore the missing relation is not a choice among ordinary row/column
  traversals. V34 is rejected without a preservation or full gate.

## Accepted experiment: v35 topology-guided nested target traversal

Parent: accepted v32 `candidate-e9c00d0968c2832a`

Observed disequilibrium:

- the multi-row targets occupy a common column lattice;
- one otherwise expected parent slot contains a non-neutral connector instead
  of a target;
- that connector's appearance matches the enclosing border of another target
  row, making the second row a plausible child scheme rather than a sibling;
- a flat row or column traversal cannot express “resume the parent after
  applying the child.”

Preregistered mutation:

- preserve v32's exact reference/selector attribute bijection and v33's exact
  target cardinality;
- infer two to four target rows on a shared coordinate lattice;
- infer each row's container attribute only from nearby rendered pixels;
- interpret a non-neutral missing lattice slot as a child link only when its
  attribute matches exactly one other row container;
- require exactly one root, an acyclic graph, no repeated child, no unresolved
  slot, and exact emitted-target cardinality;
- traverse each row left-to-right, recursively expand a linked child at its
  connector slot, then resume the parent;
- cap the construction at four rows and twelve targets and otherwise abstain.

Predicted `sb26` level-2 traversal:

- emit the first two parent targets;
- expand all four targets in the linked child row;
- resume and emit the final parent target;
- execute seven select/apply pairs plus commit, so a success should change the
  per-level action trace from `[9, 391]` to a prefix of `[9, 15, ...]`.

Falsifier:

- the advisor is silent unless every structural invariant above is satisfied;
- reject v35 if the rendered graph is not inferred, the predicted 15-action
  program does not advance level 2, or any accepted completion regresses.

Evidence:

- two frozen `sb26` target runs reproduced 2/8 levels and
  `[9, 15, 376]`;
- the source-matched six-game v32 control reproduced 12 inherited levels and
  14.2100364486/100;
- v35 preserved every inherited action count and added only `sb26` level 2,
  reaching 13 levels and 15.1359623745/100 in that gate;
- the full current-source v32 control reproduced 12/183 and
  `3.4104087476575016/100`;
- the full v35 candidate reached 13/183 and `3.632630969879724/100` with
  complete 25/25 coverage and 10,000 actions;
- 163 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, the prize audit is technically ready, and the exact
  candidate exported without translation.

V35 is accepted. The earned claim is narrow: a rendered occupied slot can
parameterize recursive expansion of one uniquely matched child container and
resume its parent. This does not establish general recursion, cross-game
transfer, a completed game, or a Kaggle leaderboard score.

## Rejected experiment: v36 bidirectional nested scheme composition

Parent: accepted v35 `candidate-7c659587fffbceb8`

Observed disequilibrium:

- v35 reaches `sb26` level 3 in `[9, 15]` and then spends 376 actions without
  progress;
- the ordered reference still contains seven distinct attributes;
- the nested containers now contain seven distinct payload objects with the
  exact reference attribute set;
- their already earned depth-first container traversal yields the exact
  reference order;
- a single lower row contains seven identical neutral outputs, reversing the
  source and target roles learned on level 2.

Preregistered mutation:

- retain v35's bounded container graph and depth-first expansion unchanged;
- add an exact-off inverse composition only when the nested payload attributes
  form an exact bijection with the ordered reference;
- require one lower neutral row with exact cardinality and uniform object
  shape, area, and appearance;
- require the nested traversal's payload-attribute sequence to equal the
  ordered reference sequence exactly;
- execute `select(nested payload) -> apply(neutral output)` while traversing
  the nested source and the output row left-to-right, then commit;
- cap the same graph at four rows and twelve payloads and abstain on every
  ambiguity.

Predicted `sb26` level-3 result:

- select and apply seven nested payloads in depth-first order;
- commit after fourteen complex actions;
- advance in exactly 15 actions, changing the trace prefix from
  `[9, 15, 376]` to `[9, 15, 15, ...]`.

Falsifier:

- reject v36 if it does not infer the exact rendered source traversal, if its
  predicted 15-action program fails to advance level 3, or if the current-
  source v35 control or any accepted completion regresses.

Result:

- the apparent heterogeneous nested-source frame was a transient post-win
  frame rather than the stable next puzzle;
- compact inference telemetry reported `no-structural-candidate` on the stable
  level-3 frame, so the inverse program never executed;
- the frozen run reproduced v35 at 2/8 levels, 8.3333333333/100, and
  `[9, 15, 376]`;
- v36 is rejected without wider gates. The negative result demonstrates why
  frame phase must be distinguished before assigning structural meaning.

## Accepted experiment: v37 enclosure-grounded sibling composition

Parent: accepted v35 `candidate-7c659587fffbceb8`

Observed disequilibrium:

- the stable `sb26` level-3 frame preserves the ordered reference, shuffled
  selector bijection, seven neutral targets, and nested connector semantics;
- the root contains three neutral targets and two occupied connector slots;
- each connector matches a separate child enclosure, and the two sibling
  enclosures share the same vertical coordinate;
- v35 groups targets by y-coordinate, merges both siblings into one false
  container, observes incompatible left/right border attributes, and abstains.

Preregistered mutation:

- retain v35's row-grounded topology as an exact fallback;
- additionally detect only exact rectangular outline components that strictly
  enclose two or more neutral targets;
- assign every target to exactly one smallest enclosing rectangle;
- infer a shared horizontal slot pitch from the complete neutral-target set;
- within each enclosure, span only from its leftmost to rightmost target and
  interpret missing lattice positions as child links only when the bounded
  slot neighborhood has one attribute matching exactly one other enclosure;
- require two to four enclosures, one root, an acyclic graph, no repeated
  child, exact target coverage, and at most twelve targets;
- traverse each enclosure left-to-right, recursively expand each child at its
  connector, and resume the parent.

Predicted `sb26` level-3 traversal:

- emit the first root target;
- expand the first two-target child;
- emit the middle root target;
- expand the second two-target child;
- emit the final root target;
- execute seven select/apply pairs plus commit, changing the trace prefix to
  `[9, 15, 15, ...]`.

Falsifier:

- reject v37 if exact enclosures or unique links cannot be inferred, if the
  predicted 15-action program fails to advance level 3, or if any accepted
  completion regresses.

Evidence:

- two frozen `sb26` target runs reproduced 3/8 levels and
  `[9, 15, 15, 361]`;
- the current-source v35 target control reproduced 2/8 and `[9, 15, 376]`;
- the source-matched six-game v35 control reproduced 13 inherited levels and
  15.1359623745/100;
- v37 preserved every inherited action count and added only `sb26` level 3,
  reaching 14 levels and 16.5248512634/100 in that gate;
- the process-isolated 25-game v35 control reproduced 13/183 and
  `3.632630969879724/100`;
- the process-isolated v37 candidate reached 14/183 and
  `3.9659643032130574/100` with 25/25 coverage and 10,000 actions;
- 166 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, the prize audit is technically ready, and the exact
  candidate exported without translation.

V37 is accepted. The earned claim is narrow: exact rendered enclosures can
ground distinct sibling procedures at the same visual height, allowing their
bounded recursive expansion and parent resumption. This is not evidence of
general object hierarchy, cross-game transfer, a completed game, or a Kaggle
leaderboard score.

## Rejected experiment: v38 connector relocation as topology construction

Parent: accepted v37 `candidate-445450df91872736`

Observed disequilibrium:

- v37 reaches `sb26` level 4 in `[9, 15, 15]` and then spends 361 actions
  without progress;
- the stable decision frame has one five-target parent enclosure and one
  two-target child enclosure but no parent connector, so v37 correctly finds
  two roots;
- the child contains one filled object whose attribute matches its enclosing
  border and whose horizontal lattice coordinate uniquely aligns with a
  neutral parent slot;
- moving a filled object into a neutral slot is already an evidenced action
  schema; relocating this marker would make the parent slot a child link and
  its vacated child position a neutral payload slot, conserving seven values.

Preregistered mutation:

- retain all v37 topology rules and fallbacks;
- detect exactly one filled marker strictly inside a child enclosure whose
  attribute matches that enclosure;
- require its x-coordinate to align with exactly one neutral target in a
  different enclosure on the shared pitch lattice;
- require that relocating the marker yields one rooted, acyclic two-enclosure
  graph with exact reference/selector/target cardinality;
- prepend `select(marker) -> apply(aligned parent slot)`;
- treat the vacated marker position as a child target, expand the child at the
  new parent link, resume the parent, fill the seven values using the exact
  reference/selector bijection, then commit;
- permit exactly one relocation between exactly two enclosures and at most
  twelve values;
  abstain on every ambiguity.

Predicted `sb26` level-4 traversal:

- emit the first parent target;
- expand the relocated marker's old position and the two existing child
  targets;
- resume the final three parent targets;
- use two relocation actions, fourteen select/apply actions, and commit,
  changing the trace prefix to `[9, 15, 15, 17, ...]`.

Falsifier:

- reject v38 if the unique aligned relocation is not inferred, if the
  predicted 17-action program fails to advance level 4, or if any accepted
  completion regresses.

Evidence:

- the frozen candidate inferred the unique relocation and emitted the exact
  predicted 17-action program;
- the connector-color selector remained outlined across the level transition,
  so the offspring normalized filled and outlined rectangular selectors before
  recovering the exact color bijection;
- selecting the filled child marker and applying it to the aligned parent slot
  produced no rendered change: the marker remained at `(25, 36)` and the
  parent slot remained neutral at `(25, 22)`;
- both frozen candidate runs and the source-matched exact-off control reproduced
  3/8 levels, 16.6666666667/100, and `[9, 15, 15, 361]`.

V38 is rejected. The negative result distinguishes structural plausibility from
causal affordance: appearance and alignment did not establish that the marker
was movable. The exact-off implementation and cognitive telemetry remain as
evidence; v38 was rejected without promotion.

## Accepted experiment: v39 evidenced shape-goal translation

Parent: accepted v37 `candidate-445450df91872736`

Observed disequilibrium:

- accepted v37 completes 0/8 `ar25` levels and spends all 400 actions;
- its audit trace spends 371 actions on coordinate-varying clicks, overwhelmingly
  without rendered change, and never constructs a successful scheme;
- a rendered black-box probe shows two interior objects translating after plain
  actions while a third interior object remains stationary;
- exactly one moving object and the stationary object have identical area and
  normalized shape despite different attributes;
- the verified development-only sequence of five repetitions of one horizontal
  action followed by ten repetitions of one vertical action aligns that mover
  with the stationary shape and advances level 1 in 15 actions, versus the
  32-action human baseline.

Preregistered mutation:

- retain all v37 policies and add one exact-off advisor before undirected
  exploration;
- probe only represented non-reset, non-coordinate action tokens, at most once
  each, until both a unique shape goal and a goal-reducing displacement are
  grounded; a first displacement away from the goal does not stop probing;
- accept a displacement only when one bounded interior component preserves its
  attribute, area, normalized shape, and bounding-box dimensions under a pure
  translation;
- identify a goal only when that mover has exactly one differently attributed
  interior component with identical area and normalized shape that remains
  stationary across the same transition;
- bind the action token to the observed mover translation, then repeat only an
  evidenced action whose predicted translation strictly reduces Manhattan
  displacement to the stationary shape without overshooting either axis;
- require two exact disjoint-frame confirmations before carrying an evidenced
  translation through partial occlusion; when the predicted mover and target
  masks intersect, preserve their latent anchors for at most four further
  non-overshooting applications of that same token, require a rendered change
  after every non-terminal application, and require progress by exact predicted
  overlap;
- arbitrate after the accepted select/apply and cyclic advisors but before
  productive-role reuse and undirected exploration;
- reset the grounded translations and shape goal on every level transition,
  cap operative applications at 32 per level, and abstain on ambiguity.

Predicted `ar25` level-1 behavior:

- one probe discovers a translation away from the target;
- a second probe discovers the inverse vertical translation and is repeated
  until vertical alignment;
- a third probe discovers the productive horizontal translation and is repeated
  until exact overlap;
- advance level 1 in at most 20 actions, with 17 expected under sorted action
  probing, without a fixed action ID, coordinate, color, game ID, or source
  import.

Falsifier:

- reject v39 if no unique exact-shape mover/target pair is grounded from
  rendered transitions, if an emitted translation fails to reduce the grounded
  displacement as predicted, if a predicted-occlusion step has no rendered
  effect or exceeds four steps without progress, if level 1 does not advance
  within 20 actions, or if any accepted completion regresses.

Evidence:

- two frozen target runs reproduced 1/8 levels with `[17, 383]`, while the
  source-matched exact-off control remained 0/8 with `[400]`;
- the seven-game preservation gate kept every v37 completed-level action count
  and added only `ar25` level 1;
- the full exact-off control reproduced v37 at 14/183 across six games and
  `3.9659643032130574/100`;
- the full candidate reached 15/183 across seven games and
  `4.077075414324168/100`, with 25/25 coverage and 10,000 actions;
- 173 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, and the exact frozen candidate exported without
  translation.

V39 is accepted. The earned claim is limited to composing
transition-evidenced translations toward a unique rendered shape goal and
maintaining bounded latent identity through predicted partial occlusion.

## Accepted experiment: v40 relational-phase-conditioned translation

Parent: accepted v39 `candidate-e4c6c38c898dcc08`

Observed disequilibrium:

- v39 advances `ar25` level 1 in 17 actions but stalls on level 2 for the
  remaining 383 actions;
- level 2 still contains a unique exact-shape mover/goal pair, and v39
  correctly grounds and completes the first displacement axis;
- one plain action then reassigns 29 rare interior marker pixels from one
  persistent major host to another while preserving the major objects'
  anchors, areas, normalized shapes, and bounding boxes;
- after that visible relational phase change, an old action displacement is
  no longer valid and a previously inert action becomes the productive
  translation;
- v39 invalidates the stale prediction correctly, but probes and action effects
  are keyed only by level and action, so it never re-probes the newly active
  action in the new phase;
- two rendered black-box runs independently advanced level 2 with
  `ACTION3 × 2 -> ACTION5 -> ACTION2 × 8`, using 11 actions versus the
  50-action human baseline.

Preregistered mutation:

- retain v39 unchanged behind an exact-off flag;
- construct a phase signature only from rare small interior marker components
  assigned by containment to persistent major interior hosts, using
  host-relative offsets and normalized host structure;
- ignore edge-touching sparse timer/border components and mover/goal
  translation when computing phase;
- recognize a phase-transition token only when the marker-host signature
  changes while the mover and target anchors, areas, normalized shapes, and
  bounding boxes remain stable;
- key translation effects, evidence, probes, and invalid actions by
  `(phase signature, action id)`;
- on an evidenced phase transition, clear pending and occlusion state,
  quarantine rather than delete the prior phase model, and permit every plain
  action one new probe in the new phase;
- select a phase-changing token only after the current phase has no evidenced
  reducer for a remaining displacement axis, and require a newly observed
  stable reducer before repeating it;
- admit at most three phase signatures and four phase transitions per level,
  probe each plain action at most once per phase, retain the 32-application
  cap, and abstain on ambiguous marker hosts or a phase cycle without a new
  reducer.

Predicted `ar25` level-2 behavior:

- ground and apply the phase-A horizontal reducer;
- discover the marker-host phase transition without treating it as a mover
  translation;
- re-probe plain actions under the new signature;
- ground and repeat the phase-B vertical reducer;
- advance level 2 within 20 actions, with about 16 expected under sorted
  probing, without a fixed action ID, coordinate, color, game ID, or source
  import.

Falsifier:

- reject v40 if the phase transition cannot be inferred solely from rendered
  marker-host reassignment, if edge animation creates a phase, if any
  prior-phase effect is applied after a phase change, if a newly probed action
  does not yield a stable reducer, if level 2 fails to advance within 20
  actions twice, or if any accepted completion regresses.

First frozen implementation result:

- source `b71ad73` and candidate `candidate-2eccd5e2dd9ae9c5` regressed
  `ar25` level 1 from 17 to 317 actions in two exact runs;
- its phase signature became structurally ambiguous during the parent's
  already-evidenced partial occlusion and permanently blocked the shape advisor
  one action before the normal win;
- the source-matched exact-off control reproduced v39 exactly at
  `[17, 383]`, so the regression is attributable to the new phase layer.

Preregistered non-interference amendment:

- when the parent has an active, twice-confirmed bounded occlusion prediction,
  a temporarily unavailable or ambiguous phase signature must preserve the
  current phase model and cannot block, change, or validate that prediction;
- only a fully visible, unambiguous marker-host reassignment may change phase;
- retain the original target falsifier and additionally require exact
  preservation of v39 level 1 at 17 actions.

First amendment result:

- source `a28e1cd` still reproduced the 317-action regression twice;
- selection-time ambiguity was preserved correctly, but response-time phase
  observation compared signatures while the mover was already partially
  occluded, treated the temporary relation as untracked, and blocked before
  the final parent action;
- the exact-off control again reproduced `[17, 383]`.

Second non-interference amendment:

- while a twice-confirmed occlusion continuation is active, phase observation
  itself must abstain before comparing marker-host signatures;
- phase evidence may neither be created nor invalidated from a transition in
  which the parent cannot fully observe its mover/target pair;
- a synthetic response-time test must demonstrate that an apparent signature
  change during predicted occlusion leaves the phase model and parent advisor
  operative.

Accepted evidence:

- final source `5bb1ac6` reproduced `[17, 17, 366]` twice on `ar25`;
- the source-matched exact-off control reproduced v39 at `[17, 383]`;
- telemetry grounded exactly two phase models and one marker-host transition,
  then learned the formerly inert phase-B reducer without applying a stale
  phase-A vector;
- the seven-game gate preserved every inherited completed-level action count,
  scoring `15.354634416237108/100` versus the exact-off control's
  `14.560983622586315/100`;
- the process-isolated 25-game candidate reached 16/183 across seven games and
  `4.29929763654639/100`; the exact-off control reproduced v39 at 15/183 and
  `4.077075414324168/100`;
- 178 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, and the exact candidate exported without translation.

V40 is accepted. The earned claim is limited to conditioning learned action
semantics on one explicitly rendered marker-host relation while conserving
the old phase model and abstaining during bounded latent occlusion.

## Rejected experiment: v41 committed-trajectory causal state

Parent: accepted v40 `candidate-76f2aac768d8cdb0`

Observed disequilibrium:

- v40 and its exact-off v39 parent both solve 0/7 `g50t` levels, spend all 400
  actions, and reset three times;
- the raw rendered stream contains 184 distinct full frames, but excluding a
  monotone boundary countdown leaves only 18 observations and 14 stable board
  configurations, so the global frame digest greatly overstates causal state;
- a movable near-filled enclosure hosts a small marker, while a larger
  stationary enclosure with a compatible hosted-marker relation supplies a
  rendered receptacle;
- one translation can be repeated to a blocked endpoint, after which a
  non-translation action visibly returns the mover to its origin and changes a
  persistent phase glyph;
- later interventions move a fresh congruent mover while an old congruent
  object independently replays the previously enacted path, demonstrating
  that the visible stable board alone is not Markov;
- a rendered black-box development search advanced level 1 twice in 17 actions
  with one concrete route. That route is feasibility evidence only and must
  not appear in the deployed policy.

Preregistered mutation:

- retain v40 unchanged behind an exact-off
  `enable_committed_trajectory_planning` flag;
- ground a mover from normalized occupancy, area, enclosure topology, and
  hosted-marker relations, and ground a unique compatible stationary
  receptacle without using color values or absolute positions;
- learn plain-action translation roles and inverse roles from rendered
  interventions, requiring consistent mover displacement while the
  receptacle remains stable;
- construct at most four endpoint macros from evidenced translations, with
  trajectories capped at 16 roles, and recognize an endpoint only when a
  previously productive translation becomes blocked;
- recognize a provisional commit only after at least two enacted trajectory
  steps, a blocked endpoint, a non-translation return of the mover to its
  origin, and a persistent rendered phase-relation change;
- carry the committed macro and replay cursor in an advisor-private causal
  state instead of aliasing solely by the current frame;
- validate autonomous replay by observing an old congruent mover follow at
  least two saved trajectory steps while the fresh mover follows independently
  selected actions; reject ambiguous identity or replay divergence;
- learn a bounded action-independent nuisance model only for a
  boundary-connected one-cell strip after at least four transitions spanning
  three actions, and exclude only that evidenced nuisance from the private
  stable state;
- plan over learned translations, the committed macro, and replay cursor with
  at most 64 causal edges, depth 16, and 20 executed planned actions;
- arbitrate after accepted select/apply and cyclic advisors, but before v39
  shape-goal translation and generic productive-role reuse; once grounded, the
  advisor retains priority until completion or explicit falsification.

Forbidden embedded information:

- no `g50t` identifier, fixed coordinate, concrete color, fixed action ID,
  discovered route, route length, source import, or fresh-environment replay;
- endpoint choice must follow a structural goal/blocker relation and learned
  effects rather than the development route;
- only environment-reported level advancement counts as success.

Predicted `g50t` level-1 behavior:

- identify the mover/receptacle relation and probe plain actions online;
- learn two translation axes and their inverses;
- construct and commit a target-reducing endpoint macro;
- retain that macro as latent causal state while validating independent replay;
- move the fresh object along the complementary target-reducing trajectory;
- advance level 1 within 30 actions twice, with roughly 24 expected from
  online probing, without any embedded concrete solution.

Synthetic invariance gates:

- recolor, translate, reflect, and consistently permute action IDs while
  preserving the same abstract macro and reflected plan;
- alias an evidenced monotone boundary clock to one private causal state while
  separating an interior mover displacement;
- accept a trajectory-grounded commit and reject origin resets without
  trajectory history, marker-only changes, and failed returns;
- validate independent ghost replay and reject objects that both follow the
  current action;
- solve original and mirrored two-arm blocker/receptacle fixtures solely from
  online transitions;
- abstain on ambiguous receptacles, inconsistent effects, excess endpoints, or
  replay divergence, and enforce every memory/search cap.

Falsifier:

- reject v41 if it cannot reconstruct the causal program from a fresh rendered
  stream, if the boundary countdown drives its private causal state, if commit
  or replay evidence is accepted without the preregistered dependencies, if
  any invariance gate fails, if `g50t` level 1 does not advance within 30
  actions twice, or if any accepted v40 completion regresses.

Observed result:

- every v41 target run remained at **0/7 `g50t` levels and 0 score** under 400
  actions;
- the final v41h run learned all four translation effects, a four-step macro,
  four autonomous replay validations, and 21 contextual blocked edges;
- bounded A* and replay timing repairs increased causal-plan execution, but
  the agent exhausted its 20 planned-action cap or reached no causal plan;
- same-level memory conserved action semantics and obstacles across deaths,
  while failure-driven variation alternated the committed axis, but neither
  produced environment-reported advancement;
- the preregistered requirement of level 1 within 30 actions twice is
  falsified. V41 is not promoted and v40 remains accepted.

A separate research-only Gemma 4 E2B hybrid probe also scored zero on 40
`g50t` actions. It returned parseable choices but failed to ground its verbal
hypotheses into causal action semantics. It is not symbolic or
Kaggle-compatible and is rejected as a runtime policy head.

## Accepted experiment: v42 substrate-topology belief planning

Parent: accepted v40 `candidate-76f2aac768d8cdb0`; v41 supplies rejected
diagnostic code only.

Observed disequilibrium:

- v41 treated every in-bounds lattice coordinate as navigable, although the
  rendered board distinguishes a dominant connected substrate from background
  holes;
- it consequently spent its bounded plan learning point collisions in
  structurally impossible regions;
- interior non-substrate overlays can move autonomously, so a no-effect edge
  against one is not a permanent wall and must not survive a retry as static
  topology.

Preregistered mutation:

- infer translation step sizes only from intervention-grounded effects;
- enumerate at most 128 lattice anchors, aligned to the grounded mover origin,
  whose centers lie inside the dominant interior connected component's bounds;
- admit anchors rendered with the dominant substrate, the grounded mover or
  receptacle relation, or a non-background interior overlay;
- classify non-substrate overlay anchors as uncertain gates and background
  anchors as structural exclusions;
- plan with bounded A* only over admitted anchors;
- retain learned action effects across same-level retries, but clear
  episode-specific blocked edges and recompute topology from the new frame;
- retain v41's bounded latent macro and replay state, while making no use of a
  game identifier, fixed coordinate, concrete color, source code, or recorded
  route.

Synthetic gates:

- translation and reflection produce correspondingly transformed topology;
- consistent action-ID permutation produces the correspondingly permuted
  first plan action;
- background holes are excluded, while an interior overlay is represented as
  an uncertain gate;
- topology and search remain within their declared caps.

Prediction and falsifier:

- predict environment-reported completion of `g50t` level 1 within 40 actions
  on two fresh exact runs;
- reject v42 if either target run fails, any synthetic equivariance/cap gate
  fails, or any implementation embeds public-game-specific information;
- run accepted-win preservation and full-suite gates only after both target
  runs pass. V40 remains accepted until every promotion gate passes.

V42a result:

- the first 40-action run solved 0/7 levels;
- it inferred 28 bounded topology nodes and 10 uncertain overlay gates, then
  executed five topology-planned actions;
- after a collision at an uncertain gate, removing that one edge disconnected
  every geometric route, and the advisor incorrectly disabled itself even
  though a safe backtrack could advance autonomous gate state;
- v42a is falsified and not promoted.

Preregistered v42b accommodation:

- when and only when an evidenced uncertain-gate collision cuts every route,
  select one admitted, currently unblocked topology edge as a bounded
  information action;
- prefer a rendered substrate node over another uncertain node, advance the
  world once, clear transient collision evidence after actual movement, and
  replan;
- preserve the same 20 planned-action cap and 40-action target prediction;
- reject v42b if the information action is chosen without an uncertain gate
  and a disconnected plan, if equivariance fails, or if level 1 does not
  advance within 40 actions twice.

V42b result:

- two fresh 40-action `g50t` runs completed level 1 at action 29 with exact
  allocation `[29, 11]`;
- both runs used two bounded gate-refresh information actions and validated all
  four committed replay steps;
- two process-isolated eight-game gates were identical, preserved every v40
  completed-level action count, and added only `g50t` level 1;
- the full 25-game run solved 17/183 levels across eight games, completed 0/25
  games, used 10,000 actions, and scored `4.442154779403533/100`;
- 191 tests passed with three skipped; Ruff, mypy, generic smoke,
  exact-candidate smoke, export, and inference-fingerprint verification passed;
- frozen inference source is `0bc1c52`; candidate
  `candidate-8c51fecdfdb99959` is accepted.

## Active experiment: v43 enacted-operation replay

Parent: accepted v42 `candidate-8c51fecdfdb99959`

Observed disequilibrium:

- on `g50t` level 2, v42 grounded four translations, committed a three-step
  endpoint macro, and detected the first autonomous replay state;
- rendered diagnostic frames then showed replay anchors at the prior probe,
  restored origin, and alternate-axis probe states;
- the environment was replaying the complete successful pre-commit
  intervention history, while v42 predicted only the retrospectively selected
  endpoint suffix and falsely declared divergence;
- this is a general reflecting-abstraction error: a replayable operation is
  the enacted coordination, including successful inverses, not merely its
  final goal-directed suffix.

Preregistered mutation:

- append every successful mover displacement during probe, restoration, and
  endpoint construction to one ordered enacted path;
- preserve repeated anchors because returning to an earlier rendered state is
  an operative inverse, not redundant data;
- on commit, retain that full path as private replay state while keeping the
  endpoint suffix separately for commit evidence;
- cap the enacted path at 32 anchors and reject overflow;
- validate replay against the enacted path with the existing pause and
  synchronous-onset rules;
- embed no game identifier, coordinate, color, action ID, source data, or
  recorded route.

Prediction and falsifier:

- the synthetic replay fixture must preserve probe/inverse order under
  reflection and consistent action-ID permutation;
- on a fresh 80-action `g50t` run, v43 must preserve level 1 at action 29 and
  avoid `replay-diverged` during the first level-2 committed sequence;
- reject v43 if level 1 regresses, the full enacted path does not predict the
  observed replay prefix, any cap/equivariance gate fails, or no additional
  environment-reported progress is achieved in a later bounded target
  refinement. V42 remains accepted until all promotion gates pass.

V43a result:

- the first 80-action run regressed `g50t` level 1 to 0/7;
- the full eight-anchor enacted path was retained, but the fresh mover's first
  action followed the same displacement as replay step 1, causing exact visual
  overlap and preventing replay identity from being observed;
- v43a is rejected under its preregistered preservation falsifier.

Preregistered v43b accommodation:

- derive first-step independence from the vector between the operation origin
  and the first enacted replay anchor, rather than from the endpoint suffix;
- forbid only actions parallel to that first enacted vector on the first
  fresh-mover plan step, then release the constraint after replay identity is
  grounded;
- require synthetic action-ID permutation and axis-reflection equivariance;
- retain the 80-action target: level 1 at action 29 and no false level-2
  replay divergence. V42 remains accepted if either condition fails.

V43b result:

- the fresh and replaying movers separated on replay step 1;
- on replay step 2, the fresh mover returned to the operation origin exactly
  when the autonomous mover replayed the inverse restoration to that origin;
- identity became visually merged and v43b regressed level 1 to 0/7, so it is
  rejected.

Preregistered v43c accommodation:

- represent the immediate joint-state constraint
  `fresh_next_anchor != predicted_replay_next_anchor`;
- before each bounded A* call, forbid only first actions whose learned effect
  would place the fresh mover on the next enacted replay anchor;
- replan after every rendered transition, so the constraint follows repeated
  anchors and inverses without embedding a route;
- preserve the pre-onset axis-separation rule, caps, reflection, and action-ID
  equivariance;
- retain the exact 80-action target and reject on any level-1 regression or
  false level-2 replay divergence.

V43c result:

- level 1 completed in 27 actions, improving accepted v42 by two actions;
- all eight level-1 enacted replay anchors and all nine level-2 enacted replay
  anchors validated without divergence;
- identity-safe detours left the fresh mover four lattice moves from the
  level-2 target when the fixed 20-step plan cap fired at action 57;
- v43c earns its replay representation but has not yet earned promotion
  because it adds no environment-reported level.

Preregistered v43d accommodation:

- replace the fixed 20-step cap with
  `min(32, 20 + committed_enacted_path_length)`;
- the extra allowance is therefore paid for by the evidenced operation whose
  joint-state avoidance created the detour, not by a game or route constant;
- retain all topology/search caps and the 80-action total target budget;
- predict `g50t` level 2 completion within 80 actions while preserving level 1
  at no more than 29 actions;
- reject if the dynamic cap exceeds 32, activates without a committed enacted
  path, regresses level 1, or fails to add level 2.

V43d result:

- level 1 remained at 27 actions and both enacted replays remained fully
  validated;
- the added nine plan steps repeated the same
  `approach gate -> collide -> one-step backtrack` cycle;
- the autonomous gate returned to the same blocking phase after each
  two-transition cycle, so v43d added no level and is rejected.

Preregistered v43e accommodation:

- count failures of each uncertain state-action edge separately from transient
  current-plan blocking;
- assign that edge a cooldown of `min(4, failure_count)` successful mover
  transitions before it can be planned again;
- decrement cooldown only after observed mover displacement, never after a
  no-effect or arbitrary action;
- while the failed edge is cooling down, use the existing safe topology
  information action, thereby varying excursion length without a route,
  coordinate, action ID, or assumed period;
- clear failures and cooldowns on level/reset boundaries and cap both by the
  existing topology edge bound;
- predict both `g50t` levels 1 and 2 within 80 actions, with level 1 no slower
  than 29; reject on any preservation, cap, or progress failure.

V43e result:

- cooldowns grew from one through four successful transitions as predicted;
- the agent nevertheless chose the same safe return operator at the first
  branch, so longer excursions remained in the same vertical orbit;
- level 1 remained at 27 actions, but level 2 did not advance; v43e is
  rejected.

Preregistered v43f accommodation:

- count selected gate-refresh actions by learned action role within the level;
- among admitted unblocked refresh edges, prefer the least-used action before
  destination uncertainty and evidence tie-breaks;
- increment the count only when the advisor actually selects a refresh action;
- require consistent action-ID permutation to permute the selected role when
  usage evidence is permuted;
- cap counts by the finite action family and clear them at level/reset
  boundaries;
- retain the 80-action two-level prediction and reject on any v42
  preservation or progress failure.

V43f result:

- level 1 remained at 27 actions, but level 2 again exhausted the remaining
  53 actions without advancing;
- refresh-role usage diversified the chosen safe actions but did not escape
  the phase-locked uncertain-gate cycle;
- the two-level prediction is falsified, so v43f is rejected and no
  preservation or full-suite gate is warranted.

## Rejected research hybrid: symbolic core with Gemma arbitration

Question:

- can Gemma add value as a bounded component inside the agent's brain, rather
  than replacing the symbolic agent or acting as the development-time critic?

Architecture:

- retain the full symbolic controller and v42 genome configuration;
- use the current experimental enacted-replay/gate substrate, matching the
  v43f source under test;
- consult local Gemma 4 E2B only after two evidenced gate failures, planner
  disablement, or a causal-plan cap;
- expose only grounded legal candidates, learned displacement roles, explicit
  gate failures, refresh usage, current/target anchors, recent actual outcomes,
  and the symbolic proposal;
- install Gemma's selected action as the real symbolic `Decision` before
  priming and trace recording, so structural credit follows the action taken;
- fall back to the symbolic proposal on malformed or out-of-range output.

Falsifier:

- require `g50t` level 2 within the fixed 80-action target while preserving
  level 1 at no more than 29 actions;
- reject if the hybrid merely matches v43f, loses level 1, produces ungrounded
  candidate/action semantics, or requires continuous expensive arbitration.

Observed result:

- **1/7 levels**, `[27, 53]`, score `3.5714285714`: exactly the v43f symbolic
  control and therefore no task gain;
- 27 consultations yielded 22 accepted symbolic proposals, five overrides,
  and six safe fallbacks;
- at least one override's prose named `ACTION4` while candidate index 4
  actually selected action 5, reproducing the grounding defect;
- the run took roughly 5.5 minutes on the local CPU server versus seconds for
  the symbolic control;
- the hybrid is rejected. Future LLM use, if any, should be one bounded typed
  model-mutation proposal followed by symbolic execution and falsification,
  not continuous action arbitration.

## Rejected experimental branch: v28 object and temporal primitives

V28 implemented content-free persistent components, composite regions,
enclosures, normalized shape forms, connected frame differences, discrete
object flow, and primitive-grounded intervention provenance. The full
offspring added `lp85` and `sp80`, but lost `tn36` and slowed `lf52` and
`r11l`, scoring `2.8820272500/100`. The ontology remains behind exact-off
genome flags, but none of its active policy traits are inherited by v29.

## Active experiment: v44 action-family fairness interaction

Parent: accepted v42 `candidate-8c51fecdfdb99959`.

Observed disequilibrium:

- a fresh five-game v42 audit reproduced `sp80` at 0/6 after 400 actions,
  spending 388 decisions on untried state interventions and resetting 12
  times;
- the rejected v28 full offspring nevertheless completed `sp80` level 1 in
  329 actions;
- v28's factorial controls show that neither hierarchical action-family
  fairness alone nor productive-role reuse without fairness solved `sp80`;
- the successful v28 run used 281 family-balanced interventions and 107
  responsive-role reuses, suggesting an interaction between broad
  action-family coverage and causal exploitation rather than a visual
  primitive-specific solver;
- accepted v42 already contains the bounded productive-role reuse mechanism,
  so enabling fairness is a clean one-field variation on the accepted genome.

Preregistered mutation:

- enable only `enable_hierarchical_action_fairness` relative to the accepted
  v42 genome;
- retain the existing finite legal-action family representation, state graph,
  eight-trial productive-role cap, all accepted structural advisors, and
  400-action budget;
- rank untried interventions first by global action-family use, then
  state-local family use, exact-token use, and stable token order;
- embed no game identifier, action ID, coordinate, color, route, or source
  information.

Prediction and falsifier:

- predict environment-reported completion of `sp80` level 1 within 400 actions
  on a fresh isolated run;
- require both hierarchical-family and bounded productive-reuse decisions to
  be operative before attributing a success to their interaction;
- reject v44 if `sp80` remains at zero, if productive reuse exceeds eight
  trials per level, if a complete fairness round fails to cover every legal
  action family exactly once, or if any later preservation gate regresses an
  accepted completion;
- only complete-round coverage is permutation-invariant; deterministic order
  inside an evidence-free tie is an explicit action-ID protocol tie-break and
  is not claimed as semantic action-permutation equivariance;
- run a second exact target and the eight-game accepted-win gate only after the
  first target qualifies. V42 remains accepted otherwise.

V44 result:

- action-family fairness was fully operative, issuing 387 family-balanced
  interventions with nearly uniform action counts;
- `sp80` nevertheless remained at **0/6 levels** after 400 actions and 13
  resets;
- the run learned four responsive roles but never reached one bounded
  productive-role reuse trial, whereas the historical v28 success learned five
  roles and issued 107 reuses across retries;
- the one-field interaction prediction is falsified. V44 is rejected.

## Active experiment: v45 primitive-grounded family reuse

Parent: rejected v44 one-field diagnostic; accepted parent remains v42.
Historical contributor: rejected v28
`candidate-71007b83cd0d153d`.

Observed disequilibrium:

- v44 balanced all six legal action families but represented each coordinate
  click as a distinct token/object grounding, so coordinate changes did not
  become a reusable causal click role before a retry;
- v28's visual primitive grounding can map a click to a bounded
  `multicolor_region` or `enclosed_region` role using normalized shape and
  primitive properties;
- v28 primitive grounding without fairness did not solve `sp80`, and v44
  fairness without primitive grounding did not solve it; their conjunction is
  the smallest remaining explanation of the historical success.

Preregistered mutation:

- relative to v44, enable only visual primitive perception and primitive
  action grounding;
- keep temporal primitives, starter schemas, preregistered credit, and every
  other rejected v28 trait off;
- when a click lies in an admitted multicolor/enclosed primitive, bind its
  role to normalized primitive kind, area, shape, and properties rather than
  absolute coordinate or concrete color;
- retain family-balanced exploration and the existing eight-trial
  productive-role cap per retry;
- abstain from primitive grounding outside an exact represented primitive and
  embed no game identifier, coordinate, color, action ID, or route.

Prediction and falsifier:

- predict `sp80` level 1 within 400 actions, with at least one
  primitive-grounded click role and at least one bounded productive-role reuse;
- reject if the target stays at zero, no primitive role is operative, reuse
  exceeds its cap, or the primitive representation changes under translation
  or color permutation;
- only after a qualifying first run, reproduce the target and test every
  accepted v42 completion.

V45 result:

- visual perception produced two multicolor-region primitives per frame, but
  the official result and every action/state metric were exactly identical to
  v44: 0/6 levels, 387 fairness decisions, 13 resets, four responsive roles,
  and zero productive reuses;
- the exact historical v28 genome also failed identically on current source,
  although it solved `sp80` at source `3a97b067`;
- source comparison isolated the drift: v29 added a 32-intervention maturity
  threshold and resets `level_interventions` to zero on every `GAME_OVER`;
- `sp80` retries terminate before 32 interventions, making mature productive
  reuse unreachable regardless of accumulated same-level failures;
- v45 is rejected. Primitive grounding was perceptually present but causally
  inoperative.

## Active experiment: v46 cross-retry maturity conservation

Parent genome: accepted v42 plus the rejected v44 fairness diagnostic.

Observed disequilibrium:

- a `GAME_OVER` retry clears failed episode cursors and plans correctly, but
  it also clears the maturity evidence that 32 interventions were attempted on
  the same unsolved level;
- this conflates episode policy state with level-level epistemic experience;
- historical v28 could exploit responsive roles after repeated failures,
  while current v44 never satisfies the later v29 maturity gate;
- the general accommodation principle is to conserve independently supported
  causal evidence across a retry while discarding the failed control episode.

Preregistered mutation:

- add an exact-off `enable_cross_retry_maturity` genome trait;
- when enabled, preserve the bounded `level_interventions` maturity counter
  across `GAME_OVER` on the same environment-reported level;
- continue clearing episode roles, program/variation cursors, per-retry
  productive trial count, cyclic/select-apply/shape/trajectory episode state,
  and transient plans exactly as before;
- clear cumulative maturity on actual level progress;
- cap cumulative maturity at the existing threshold because values above 32
  have no policy meaning;
- combine the trait with v44 family fairness and accepted productive-role
  reuse, but leave v45 visual primitives and all other rejected v28 traits off.

Prediction and falsifier:

- a synthetic retry must conserve maturity only with the new trait, reset
  per-retry reuse trials, and clear maturity on level progress;
- predict `sp80` level 1 within 400 actions, with productive reuse becoming
  operative only after the cumulative threshold and at least two failures;
- reject if reuse occurs early, exceeds eight trials per retry, maturity leaks
  across level progress, `sp80` remains at zero, or any accepted completion
  regresses in a later gate.

V46 first result and falsifier audit:

- the offspring completed `sp80` level 1 at action 391, with five responsive
  roles, 96 productive reuses, and at most eight reuses in each retry;
- cumulative maturity reached its cap after the first retry and cleared on
  level progress as intended;
- however, pragmatic disequilibrium allowed the first reuse at action 33 after
  only one completed failure, violating the preregistered two-failure
  condition;
- this run is real progress but does not qualify for promotion.

Preregistered v46b non-bypass amendment:

- for the exact-off cross-retry trait only, require two completed same-level
  failures even when pragmatic disequilibrium is already active;
- preserve the accepted default pragmatic path when the trait is off;
- retain the same maturity cap, per-retry eight-trial cap, and 400-action
  target;
- require a fresh `sp80` level-1 completion with the first reuse occurring
  only after failure two.

V46b result:

- two exact target runs completed `sp80` level 1 at action 328 with allocation
  `[328, 72]`;
- first productive reuse occurred at action 60 after exactly two completed
  failures, cumulative maturity was capped at 32, and every retry used at most
  eight reuses;
- the nine-game gate added `sp80`, improved `g50t` level 1 from 29 to 27, and
  exactly preserved `ar25`, `ft09`, `r11l`, `sb26`, and `tn36`;
- it regressed `lf52` from one level to zero and `lp85` from three levels to
  zero, so v46b is rejected and v42 remains accepted.

## Accepted experiment: v47b failure-conditioned fairness

Parent: rejected v46b diagnostic; accepted parent remains v42.

Observed disequilibrium:

- v46b's cross-retry maturity distinction produced reproducible `sp80`
  progress, but hierarchical fairness controlled every intervention from the
  beginning of every game;
- accepted `lf52` normally solves level 1 in 34 actions and accepted `lp85`
  solves level 1 in 37, before repeated same-level failure supplies evidence
  that their exploration policy should be accommodated;
- in the rejected gate, `lp85` had only one failure yet lost all three levels,
  while `sp80` required two failures before the newly valid reuse mechanism
  could activate;
- fairness is therefore an accommodation policy, not a universal prior.

Preregistered mutation:

- add exact-off `enable_failure_conditioned_fairness`;
- when enabled, hierarchical action-family ranking remains inactive until two
  completed failures on the same environment-reported level;
- before that threshold, preserve the accepted flat token-ranking policy
  exactly;
- after the threshold, balance finite legal action families using the existing
  global/state-local counts and retain cross-retry maturity plus bounded reuse;
- reset the failure gate on actual level progress, so each new level starts
  with the accepted policy;
- keep the old unconditional fairness behavior exact when the new trait is
  off.

Prediction and falsifier:

- synthetic tests must show exact flat ordering before failure two, family
  round coverage after failure two, and return to flat ordering on progress;
- predict exact `sp80` level-1 reproduction within 400 actions;
- require the nine-game gate to preserve every v42 completion, with exact
  action counts preferred and no lost level permitted;
- reject on early fairness, missing target progress, reuse-cap violation, or
  any accepted regression.

V47 result:

- two exact target runs completed `sp80` level 1 at action 196, improving the
  qualifying v46b target by 132 actions;
- the nine-game gate exactly preserved `ar25`, `ft09`, `lf52`, `r11l`,
  `sb26`, and `tn36`, improved `g50t` level 1 to 27 actions, and added
  `sp80`;
- `lp85` nevertheless regressed from three levels to zero;
- trace inspection showed that accepted `lp85` earns same-episode productive
  reuse after 32 interventions with zero failures, while v47's cross-retry
  two-failure guard incorrectly blocked that parent path;
- v47 is rejected.

Preregistered v47b zero-failure non-interference amendment:

- preserve the accepted mature-stall productive-reuse path when there are zero
  failures and pragmatic disequilibrium is active;
- suppress reuse only in the one-failure ambiguous state;
- enable conserved cross-retry maturity at two or more failures;
- leave failure-conditioned fairness unchanged: flat before failure two,
  family-balanced afterward;
- require exact target reproduction and no lost level in the nine-game gate.

V47b result:

- two exact target runs completed `sp80` level 1 at action 196 with allocation
  `[196, 204]`;
- two exact nine-game gates preserved every v42 level and action count, improved
  `g50t` level 1 from 29 to 27 actions, and added `sp80`;
- the frozen-source full suite scored `4.449696279968774/100`, solved 18/183
  levels across nine games, used all 10,000 actions, and completed 0/25 games;
- 204 tests passed with three skipped; Ruff, mypy, generic and exact-candidate
  network-disabled smoke tests, and exact export all passed;
- candidate `candidate-4c7168f7ad208c65` is accepted from frozen inference
  source `b9412202c3fd6a5c3f31e68d62127c00a0090fb6`.

## Active experiment: v48 action-independent boundary nuisance state

Parent: accepted v47b `candidate-4c7168f7ad208c65`.

Transfer audit:

- an unchanged v47b five-game audit targeted unsolved games with five to seven
  repeated same-level failures: `bp35`, `cn04`, `s5i5`, `tu93`, and `vc33`;
- the agent scored zero across 2,000 actions and 34 total levels;
- failure-conditioned fairness was selected 226, 213, 245, 245, and 245 times
  respectively, while bounded productive-role reuse was selected 48, 40, 56,
  56, and 56 times;
- four games changed all 399 observed transitions and `cn04` changed 333,
  showing that generic rendered responsiveness is too weak to identify a
  goal-relevant action under pervasive animation;
- this falsifies broad transfer from additional fairness/reuse pressure.

Observed `m0r0` disequilibrium:

- the first four plain interventions ground a symmetric two-object control
  algebra: common vertical translations and mirrored horizontal translations;
- a small outer-boundary signal then advances autonomously, including under
  three distinct plain actions;
- because the epistemic graph keys nodes by the complete frame digest, every
  boundary phase is a new state;
- the accepted agent consequently selects the same wait-like action in each
  nominally novel state instead of compiling the already observed paired
  controls or exploring the joint maze.

Preregistered v48 mutation:

- add exact-off `enable_boundary_nuisance_state_key`;
- observe only one-cell outer-boundary changes from actual interventions;
- identify a nuisance side only after at least four conserved pure translations
  of the same minority boundary pattern spanning at least three distinct
  action IDs with one consistent displacement;
- after that evidence, canonicalize only the evidenced side when constructing
  epistemic graph keys; preserve every interior pixel and every other side;
- clear nuisance evidence on actual level progress and retry, retain bounded
  transition evidence, and expose it in cognitive telemetry;
- encode no game identifier, coordinate, color, action ID, route, or known
  environment rule.

Prediction and falsifier:

- synthetic tests must reject action-dependent, shape-changing, inconsistent,
  interior, or fewer-than-three-action boundary motion and must alias only the
  evidenced side after the fourth qualifying transition;
- predict fewer than 60 distinct epistemic states and fewer than 40 selections
  of any wait-like self-loop on `m0r0` under 400 actions;
- require environment-reported `m0r0` level-1 completion within 400 actions
  before any preservation gate;
- reject if canonicalization activates without the preregistered evidence,
  erases interior structure, misses the diagnostic reductions, or does not add
  a real level. V47b remains accepted otherwise.

V48 result:

- the target remained at 0/6 levels after 400 actions;
- the preregistered conserved-translation detector never activated, the graph
  retained 147 states, and the wait-loop diagnostic was not reduced;
- direct frame inspection showed why: the boundary signal is a fixed-endpoint
  monochrome strip that grows by one cell every few interventions, not a
  fixed-shape translating pattern;
- v48 is rejected without preservation or full-suite gates.

Preregistered v48b monotone-strip accommodation:

- retain v48's pure-translation detector unchanged;
- additionally recognize a contiguous, single-color minority pattern only
  when one endpoint stays fixed and the other grows or shrinks by exactly one
  cell on each qualifying boundary transition;
- require four consistent qualifying changes spanning at least three distinct
  action IDs; unchanged frames neither count nor falsify the candidate;
- reject color, fixed endpoint, direction, contiguity, side, or step-size
  changes and preserve the same side-only canonicalization and reset rules;
- retain the original target requirement: `m0r0` level 1 within 400 actions,
  fewer than 60 graph states, and fewer than 40 wait-like self-loop choices.

V48b result:

- the monotone detector activated on the top and bottom sides and held the
  canonical graph at 25 states for the remainder of the first life;
- total state count still reached 89 across retries, and the agent remained at
  0/6 levels after 400 actions;
- after normalization, it issued distinct coordinate-bearing action-6 tokens
  such as boundary and object clicks from the same canonical state, so 294
  decisions were still classified as untried-state interventions;
- v48b is rejected: normalizing state without normalizing intervention
  allocation did not satisfy either the behavioral diagnostic or task target.

Preregistered v48c nuisance-conditioned action-family fairness:

- add exact-off `enable_boundary_nuisance_fairness`, dependent on boundary
  nuisance state keys and hierarchical action-family fairness;
- preserve v47b's flat parent policy before nuisance evidence;
- once any boundary side satisfies v48b's action-independent evidence, activate
  the existing bounded family ranking immediately, without waiting for two
  failed lives;
- retain concrete coordinate tokens inside the complex-action family; the
  mutation changes allocation across finite legal families, not click
  semantics or candidates;
- reset the evidence and its fairness trigger on retry or progress;
- predict fewer than 100 complex-action selections, fewer than 60 graph states,
  and `m0r0` level-1 completion within 400 actions;
- reject on pre-evidence fairness, missing trigger, cap/structural test failure,
  diagnostic failure, or no real level. V47b remains accepted otherwise.

V48c result:

- nuisance evidence activated family fairness at action 40, after which plain
  action counts balanced at 48 or 49 each;
- the target still remained at 0/6 levels, with 156 complex actions and 81
  graph states, violating both diagnostic predictions;
- normalization and fair allocation therefore removed two exploration
  pathologies but did not represent the coupled control problem;
- v48c is rejected without preservation or full-suite gates.

## Accepted experiment: v49b paired-object contact planning

Parent: accepted v47b `candidate-4c7168f7ad208c65`. V48-v48c supply rejected
diagnostic code only.

Observed disequilibrium:

- `m0r0` contains exactly two congruent small interior objects in a shared
  connected substrate, initially related by horizontal reflection;
- rendered interventions ground common vertical actions and mirrored
  horizontal actions; obstacles can block either object independently, so the
  operative state is a pair of anchors rather than one mover or full frame;
- v48c visited only 12 distinct pair positions in its first life despite
  balancing action families, because it had no joint operator or goal;
- a development-only black-box path was derived from the rendered substrate,
  not environment source: it navigated the two objects through different
  blocked passages and then reduced their separation on a shared corridor;
- the environment reported level-1 progress within 16 actions. This is
  feasibility evidence only; the concrete action sequence is forbidden from
  inference code and candidates.

Preregistered v49 mutation:

- add exact-off `enable_paired_object_contact_planning`;
- ground a pair only when exactly one interior object-signature class contains
  two same-color, same-area, same-shape objects related by horizontal or
  vertical reflection and surrounded by one shared substrate color;
- probe represented non-reset, non-coordinate actions once and learn an
  ordered pair of displacements from rendered object motion, including
  independently blocked components;
- require at least two consistent nonzero joint effects and reject identity,
  shape, color, or substrate ambiguity;
- infer a bounded lattice from learned displacement magnitudes and admit an
  anchor only when the translated object mask lies entirely on the shared
  substrate or either current mover mask;
- search at most 2,048 joint states and 8,192 edges for a plan that brings the
  two translated masks into contact, applying each learned joint action with
  independent obstacle blocking;
- replan after every transition, cap probing plus planned applications at 64,
  and clear the model on retry or level progress;
- expose grounding, learned effects, topology size, search expansions, plan
  length, and falsification in cognitive telemetry;
- encode no game ID, action ID, coordinate, color, route, source import, or
  target action sequence.

Prediction and falsifier:

- synthetic original/reflected fixtures and consistent action-ID permutations
  must ground correspondingly reflected/permuted joint effects and plans;
- the advisor must abstain on a third congruent object, unequal shapes,
  different substrates, inconsistent effects, non-contact topology, or any
  search/cap overflow;
- predict `m0r0` level 1 within 30 actions twice, matching the human-baseline
  scale while learning controls online;
- reject on either target failure, embedded route information, invariant/cap
  failure, or any later accepted regression. V47b remains accepted until every
  promotion gate passes.

V49 result:

- the first target grounded the pair immediately, learned four joint effects
  from five probes, inferred 55 substrate anchors, and replanned a 14-step
  contact path online;
- the two masks reached contact at action 19 and became one connected rendered
  component, after which the advisor reported `paired-identity-unavailable`;
- generic exploration eventually issued two further inward actions and the
  environment reported level-1 progress at action 34;
- the run scored `3.7073652991` for `m0r0` and proves the joint operator is
  task-relevant, but it violates the preregistered 30-action bound, so v49 is
  not yet eligible for preservation or promotion.

Preregistered v49b latent-contact continuation:

- retain the exact learned pair grounding, joint effects, topology, and plan;
- when and only when the final predicted contact action changes two separately
  tracked congruent objects into one connected component, retain that action
  as a latent contact-continuation operator instead of declaring identity loss;
- repeat only that evidenced final contact action at most twice, require a
  rendered change on each nonterminal continuation, and stop immediately on
  progress, pair reappearance, no effect, or cap;
- never enter continuation after ambiguous identity loss away from the planned
  contact edge or after an unplanned action;
- synthetic tests must distinguish planned contact merge from arbitrary object
  disappearance and enforce the two-action cap;
- predict level 1 within 24 actions twice; reject on either miss, invalid latent
  continuation, or any later accepted regression.

V49b target result:

- two fresh isolated runs matched exactly at 1/6 levels, action allocation
  `[20, 380]`, and score `4.7619047619`;
- each run used five online probes, inferred 55 level-1 substrate anchors,
  executed the same 14-step recomputed contact plan, and used one bounded
  latent-contact continuation;
- both full 400-action traces matched in action counts, advisor counts, and
  final structural telemetry;
- the target qualified for a ten-game preservation gate covering all nine
  accepted v47b progress games plus `m0r0`.

V49b accepted result:

- two fresh process-isolated ten-game gates matched exactly at
  `11.600431176112412/100` and 19 levels;
- every inherited v47b game preserved its score, completed-level action
  allocation, and structural telemetry exactly; `m0r0` added level 1 at action
  20;
- the frozen-source 25-game suite scored `4.6401724704449645/100`, solved
  19/183 levels across ten games, used all 10,000 actions, and completed 0/25
  games;
- candidate `candidate-6ee87ced5a667cae` is accepted from frozen inference
  source `83287a7c2e508313fbb52b1982a921159823895e`;
- the full report SHA-256 is
  `a21f30f0d082617d0bc042966495b208244e4e2ddae0e64c034ad67b9f84d17d`
  and candidate SHA-256 is
  `9a1ef98881ea39943162c67fcfb83cff551eef022da38c4229a9b93d5e0b841c`;
- 209 tests passed with three skipped; Ruff, mypy, generic and exact-candidate
  network-disabled smoke tests, and exact export all passed.

## Active experiment: v50 confirmed contextual pair transitions

Parent: accepted v49b `candidate-6ee87ced5a667cae`.

Observed level-2 disequilibrium:

- a fresh recording-enabled v49b run reproduced 1/6 `m0r0` levels at
  `[20, 380]` and score `4.7619047619`;
- level 2 again grounded the unique reflected congruent pair, learned four
  joint effects from five probes, and inferred 118 substrate anchors;
- at one exact joint anchor, the planner predicted ordinary downward motion,
  but the rendered successor transported both objects to the upper region and
  added opposite horizontal displacements while preserving their identities;
- v49b represents a component as either taking its global learned displacement
  or remaining blocked. It therefore ignored the unexpected successor,
  repeatedly planned through the same false geometric edge, and executed five
  identical 12-action loops before exhausting its 64 paired trials;
- the mismatch occurs at the same joint anchor under the same action and with
  the same rendered successor, so it is eligible to become a bounded
  state-conditioned transition hypothesis. A single occurrence is not enough
  to attribute an autonomous change to the selected action.

Preregistered v50 mutation:

- add exact-off `enable_paired_contextual_transitions`, dependent on paired
  object contact planning;
- after a planned pair action only, compare the observed ordered-anchor
  successor with the successor predicted by the already grounded global joint
  effect plus independent obstacle blocking;
- when identities and shapes remain grounded but the successors differ, retain
  bounded evidence keyed by `(ordered joint anchors, action role)`; confirm an
  exact contextual successor only after two matching outcomes and quarantine
  the key if outcomes conflict;
- never use the transition that first proposes or confirms an edge to score
  that same transition; confirmed edges become available only to subsequent
  planning decisions;
- in bounded contact search, substitute a confirmed exact successor for the
  hallucinated geometric successor only at its evidenced joint anchor and
  action; require both successor anchors to remain in the rendered topology;
- clear contextual edges on level progress or retry, cap evidence at 128
  state-action keys and three observations per key, and expose proposal,
  confirmation, conflict, and planner-use counts in cognitive telemetry;
- encode no game identifier, coordinate, color, fixed action ID, route, portal
  label, period, or source import.

Prediction and falsifier:

- synthetic translation/reflection and consistent action-ID permutation
  fixtures must produce correspondingly transformed/permuted contextual edges;
- one anomalous outcome must not alter planning, two matching outcomes must
  replace only the evidenced edge, and a conflicting outcome must quarantine
  it;
- on `m0r0`, predict exactly one confirmed contextual edge after the second
  repeated mismatch and no third traversal of the same 12-action loop;
- require environment-reported level-2 completion within 220 total actions on
  two fresh 400-action runs before any preservation gate;
- reject on premature confirmation, cap/equivariance failure, a third repeated
  false-edge loop, either target miss, or any later accepted regression. V49b
  remains accepted unless every promotion gate passes.

V50 result:

- the first frozen-source target reproduced v49b exactly at 1/6 levels,
  `[20, 380]`, and score `4.7619047619`;
- two distinct state-action edges were each proposed once and confirmed on
  their second identical outcome, with zero conflicts and 44 bounded planner
  uses;
- substituting the first edge changed the chosen approach, but that approach
  exposed a second false geometric edge; after both were confirmed, a third
  unmodeled approach produced the same convergent transported successor;
- the target therefore violated both the one-edge diagnostic prediction and
  the required level-2 completion. V50 is rejected without preservation or
  full-suite gates; its exact-off code remains diagnostic evidence.

## Active experiment: v51 induced convergent transport family

Parent: accepted v49b `candidate-6ee87ced5a667cae`; rejected v50 supplies
state-conditioned transition evidence only.

Observed higher-order regularity:

- v50's first confirmed edge followed action 2 from anchors
  `((18, 34), (42, 34))`; the intended right-object footprint intersected one
  excluded rendered color and both objects appeared at
  `((22, 10), (38, 10))`;
- its second confirmed edge followed action 4 from
  `((22, 34), (38, 34))`; this time the intended left-object footprint
  intersected that same excluded color and both objects appeared at the exact
  same successor;
- a later unconfirmed edge followed action 2 from
  `((14, 34), (46, 34))`; both intended footprints intersected the same
  excluded color and again converged to that successor;
- the coordinates and concrete color above are diagnostic evidence only and
  are forbidden from the runtime. The candidate must induce the shared
  relation from masks, substrate membership, and observed outcomes.

Preregistered v51 mutation:

- add exact-off `enable_paired_transport_family`, dependent on v50 contextual
  transitions;
- for each confirmed contextual edge, retain the set of colors in the two
  globally predicted mover footprints that are neither the grounded substrate
  nor mover color;
- induce one convergent transport family only when two distinct confirmed
  state-action keys have the same ordered successor and exactly one shared
  excluded trigger color; abstain on multiple destinations, an empty or
  ambiguous trigger intersection, identity loss, or a family cap of one;
- in later bounded contact search, when a proposed joint move places either
  mover footprint on the induced trigger color, use the learned convergent
  successor instead of testing another state-specific hallucinated edge;
- destination anchors must remain admitted in the current topology, and direct
  confirmed state-action successors retain priority over the family;
- clear family evidence on level progress or retry and expose family
  inductions and planner uses in cognitive telemetry;
- encode no game ID, coordinate, concrete color, fixed action ID, route,
  period, or portal name.

Prediction and falsifier:

- synthetic translation/reflection/recoloring and consistent action-ID
  permutation must preserve the induced relation while transforming its
  concrete evidence;
- two independently confirmed convergent edges are required, and divergent
  destinations or trigger colors must block induction;
- on `m0r0`, predict one family induction after the second confirmed edge,
  family use before the third previously observed trigger, and no third
  state-specific contextual proposal in that episode;
- require environment-reported level-2 completion within 220 total actions on
  two fresh 400-action runs before any preservation gate;
- reject on premature/ambiguous induction, missing family use, a third
  state-specific proposal, either target miss, or any accepted regression.
  V49b remains accepted otherwise.

V51 result:

- the first frozen-source target again scored `4.7619047619`, solved only
  level 1, and allocated `[20, 380]`;
- exactly two state-specific edges were proposed and confirmed, one convergent
  transport family was induced, and bounded search used it 846 times without
  proposing the previously observed third edge;
- the internal structural predictions therefore passed, but environment-
  reported level 2 did not advance within 220 or 400 actions, so v51 is
  rejected without preservation or full-suite gates;
- importantly, after family induction the selected contact-plan length fell
  monotonically from 19 to 11 across the remaining nine paired decisions.
  The 64-trial cap then preempted the advisor; this is evidence of a truncated
  newly valid plan, not evidence for an arbitrary global cap increase.

## Rejected experiment: v52 one post-accommodation plan allowance

Parent: accepted v49b `candidate-6ee87ced5a667cae`; rejected v50-v51 supply
contextual transition and transport-family evidence.

Preregistered mutation:

- add exact-off `enable_paired_post_accommodation_plan`, dependent on the v51
  transport family;
- preserve the base 64 paired trials until one convergent transport family is
  grounded;
- on the first subsequent bounded search that returns a contact plan of length
  `L`, retain a one-time allowance of exactly `min(L, 32)` additional paired
  trials;
- never renew, enlarge, or reset that allowance after replanning within the
  episode; clear it on environment-reported retry or level progress;
- require every executed step to remain selected by a freshly recomputed
  bounded plan, retaining all identity, topology, search, contextual-edge,
  family, and latent-contact guards;
- expose the earned allowance and effective cap in telemetry and encode no
  game ID, action ID, coordinate, color, route, expected level, or fixed
  solution length.

Prediction and falsifier:

- synthetic tests must show cap 64 before family grounding, cap
  `64 + min(L, 32)` after the first family-grounded plan, no renewal from a
  later longer plan, and reset to 64 at the next level/episode;
- on `m0r0`, predict the already evidenced 19-step allowance, continued
  monotone plan execution, and environment-reported level-2 completion within
  120 total actions on two fresh 400-action runs;
- reject on an allowance without family evidence, renewal, cap overflow,
  non-plan execution, either target miss, or any accepted regression. V49b
  remains accepted otherwise.

Observed result:

- candidate `candidate-dd6d643b11ef01a9`, frozen source `c6800d8`, earned the
  preregistered allowance of 19 and exposed the expected effective cap of 83;
- it grounded one convergent transport family, used that family 1,202 times
  in bounded search, and continued selecting freshly recomputed contact plans;
- nevertheless it reproduced only 1/6 `m0r0` levels at `[20, 380]`, scoring
  `4.7619047619` for the target and missing the required level 2 within 120
  total actions;
- the first target miss activates the preregistered falsifier, so no second
  run, preservation gate, or full-suite run is justified. V52 is rejected and
  v49b remains accepted.

The v50-v52 sequence separates three claims that must not be conflated:
state-specific transition prediction improved; a convergent local transport
family was genuinely induced; and extra planning depth executed that family.
None supplied a model of the task's terminal relation or latent phase.
Continuing to lengthen this advisor would therefore overfit search around a
missing goal abstraction.

## Active experiment: v53 content-addressed inherited schemes

Parent: accepted v49b `candidate-6ee87ced5a667cae`.

Architectural hypothesis:

- cross-run common sense should be inherited as immutable typed scheme
  definitions whose identity excludes mutable empirical confidence;
- an append-only evidence ledger should merge confirmations and
  counterexamples by definition hash;
- accommodation should produce a new definition hash while conserving the
  parent as an explicit dependency;
- the exact dependency-closed library snapshot and Merkle root should live in
  `MindConfig`, candidate identity, isolated-process JSON, cognitive telemetry,
  Kaggle notebook serialization, and the offline inference overlay;
- inherited definitions should enter the existing component-specific
  structural-credit path only when their declared grounding requirements are
  present.

Implemented substrate:

- `reflector/core/inheritance.py` defines canonical `SchemeDefinition` and
  closed `SchemeLibrary` snapshots plus content-free starter definitions;
- `reflector/evolution/inheritance.py` defines the development-only evidence
  ledger, conservative held-out promotion rule, accommodation, and genome
  embedding;
- free-form scalar mutation providers cannot edit library payloads or roots;
- isolated descendants inherit the exact snapshot while ordinary genome
  mutations change only their declared scalar/boolean trait;
- the operative explorer emits inherited definition hashes and the library
  root in telemetry and assigns grounded definitions to structural credit;
- the Kaggle overlay now includes the deterministic inference-side definition
  module. No evidence database, evolver, or LLM enters the overlay.

Preregistered first runtime audit:

- freeze the implementation before creating the candidate;
- endow accepted v49b with exactly the six content-free starter definitions,
  leaving all other v49b policy fields unchanged;
- on one accepted progress game, require the accepted level/action result to
  remain exact while the cognitive stream reports the frozen library root,
  six definitions, and at least one `scheme:inherited:<hash>` operative
  component;
- reject on changed accepted action efficiency, missing/incorrect root,
  ungrounded structural credit, serialization drift, or any embedded game ID,
  coordinate, route, color, or action constant;
- treat exact behavior plus operative telemetry only as substrate validation,
  not as a promotion or task gain. A later offspring must use an
  evidence-promoted scheme to improve a held-out real-game outcome.

First audit result:

- v53 `candidate-48c1e7c59c64c07a` reproduced accepted `r11l` level 1
  exactly at action 18 and carried the correct six-definition root through the
  official harness;
- no inherited hash appeared in a transition assessment because accepted
  v49b disables preregistered structural credit; the explorer computed the
  grounding but `SymbolicMind.prime_hypothesis` correctly ignored all
  components behind that flag;
- this activates the operative-path falsifier. V53 is rejected as substrate
  wiring evidence, not promoted.

Preregistered v53a repair:

- require `enable_inherited_scheme_library` to depend on
  `enable_preregistered_structural_credit`, and make typed library embedding
  enable that dependency atomically;
- change no other accepted v49b behavior field or inherited definition;
- rerun `r11l`; require level 1 at action 18, the same six-definition root,
  at least one transition assessment containing a
  `scheme:inherited:<definition-hash>`, and positive typed-credit structure
  count;
- reject on any missed condition. Even a pass validates infrastructure only.

V53a result:

- candidate `candidate-71b134a4f6261be8` on frozen source `a0d2528`
  reproduced `r11l` at exactly `[18, 382]` and
  `4.7619047619` for the target;
- the official cognitive stream reported all six definitions under root
  `845117a28438262834f23f4c574717e521a83f137cd92da6c2fdf3370e0900b3`;
- three action-family/object-applicable inherited hashes occurred in 390
  transition assessments, and typed structural credit reached 98 structures;
- the exact candidate passed the network-disabled Kaggle smoke and exported
  without translation. Overlay SHA-256:
  `0c71a2d66e63e8d0c7cd0167fc1dd826930769b74b1bb79c898de28f95e0cfc7`;
  notebook SHA-256:
  `7ce8541e334a435a5f5b2123ab27090e64ff40af1d77d087c8626314f184635b`;
- the infrastructure prediction passes. V53a is not promoted because it adds
  no task result and its content-free priors have not earned cultural
  inheritance evidence.

Next inheritance experiment:

- derive append-only evidence only from inherited definitions that made
  non-empty effect or goal predictions before an action;
- aggregate isolated offspring streams by content hash and evaluation
  partition, retaining falsifications and regressions;
- breed a child by embedding only the dependency-closed definitions that pass
  the held-out promotion rule;
- prove that generic starter forms cannot self-promote merely because they
  were active when unrelated progress occurred.

Implemented and structurally verified:

- the cognitive-stream compiler requires a preregistered hypothesis, an exact
  inherited hash, and a definition-specific effect or observable goal
  contract before emitting evidence;
- the real v53a `r11l` stream compiled to zero evidence events despite level
  progress, correctly preventing content-free starter schemes from
  hitchhiking;
- the breeder merges isolated ledgers idempotently, applies the held-out
  promotion rule, preserves dependency closure and previously inherited
  definitions, and embeds the selected library in a new candidate identity.

The next empirical offspring must therefore propose one risky, general
effect/goal definition from a trace diagnosis and test it on separated
development and held-out games. Do not award evidence from the source episode
used to formulate its contract.

## Active experiment: v54 relative object-ranking population

Parent: accepted v49b `candidate-6ee87ced5a667cae`.

Disequilibrium:

- v53a proves inherited hashes can receive credit, but its definitions do not
  differentiate legal actions;
- only locally constructed parameterized and relational schemes currently
  consume structural scores, so cultural inheritance remains bookkeeping
  unless a definition can select a bounded intervention;
- absolute colors, coordinates, routes, and game identities are forbidden and
  would not constitute common sense.

Preregistered code mutation:

- permit an inherited definition with operator
  `prioritize-intervention`, object grounding, a non-empty effect/goal
  contract, and exactly one supported relative ranking to select an untried
  object intervention;
- support only `smallest-area`, `largest-area`, `rarest-shape`, and
  `most-repeated-shape` rankings, computed within the current perceived scene;
- cap each definition by its immutable `resource_cap`, reject negatively
  credited definitions, retain all higher-priority independently grounded
  advisors, and expose selections, trials, and the selected rank in telemetry;
- place only the selected inherited hash on the causal hypothesis, rather than
  crediting every definition in the library.

Population and partition:

- freeze the code before candidate generation;
- create three otherwise identical v49b descendants carrying one definition
  each: smallest-area control, rarest-shape variation, and largest-area
  variation;
- use `r11l` as the development game because accepted v49b's generic object
  ordering already solves its first level at action 18;
- preregister `s5i5`, `tn36`, and `vc33` as held-out click-game probes before
  running any variant;
- allocate 400 actions per game in isolated processes. No variant may adapt
  its library between games.

Prediction and falsifier:

- smallest-area should reproduce `r11l` level 1 at action 18, demonstrating
  that the inherited advisor can express the existing relative prior;
- the rarest/largest variants must produce distinct first interventions and
  nonzero inherited selections, or the policy mutation is inoperative;
- a scheme qualifies for further inheritance evidence only if it preserves
  `r11l`, adds a held-out level or materially improves accepted held-out action
  efficiency, and yields definition-specific preregistered evidence;
- reject any game-specific payload, cap breach, missing trace attribution,
  accepted regression, or purely internal improvement. V49b remains accepted
  unless a descendant later passes the full promotion protocol.

First development population result:

- smallest-area solved `r11l` level 1 at action 16, rarest-shape at action 35,
  and largest-area completed 0/6 levels;
- the first interventions were distinct and trace-attributed:
  `(7,36)`, `(17,46)`, and `(4,4)` respectively, expressed here only as
  diagnostic observations and not encoded in any definition;
- smallest-area reported 42 selections and rarest-shape 72 despite a
  `resource_cap` of 24. The implementation cleared its counter on
  environment-reported `GAME_OVER`, confusing a retry with a new level;
- this activates the cap-breach falsifier. None of these apparent task
  outcomes qualifies as inheritance evidence and held-out games are not run
  from this source.

Preregistered v54a repair:

- retain inherited-scheme trial counts across `GAME_OVER` retries and clear
  them only on an environment-reported level advance;
- change no definition, rank, budget, advisor priority, or target partition;
- rerun the three-way `r11l` development population and require every
  definition to remain at or below 24 total trials for the unsolved current
  level;
- only after that structural condition passes may qualifying variants proceed
  unchanged to the already frozen `s5i5`, `tn36`, and `vc33` held-out set.

V54a result:

- the repaired development round respected the 24-trial per-level cap:
  smallest-area again solved `r11l` level 1 at action 16, rarest-shape at
  action 35, and largest-area remained at 0/6;
- smallest and rarest advanced unchanged to the frozen held-out set. Both
  exactly matched accepted v49b: 0 levels on `s5i5`, `tn36` level 1 at action
  123, and 0 levels on `vc33`;
- neither variant added a held-out level or improved accepted held-out action
  efficiency, so both fail the pragmatic inheritance criterion;
- evidence compilation then exposed an attribution leak: after the explicit
  ranking advisor exhausted its cap, generic object exploration reattached
  the actionable definition through ordinary grounding. This inflated each
  held-out ledger to hundreds of apparent `frame_changed` confirmations and
  allowed the `tn36` progress event to hitchhike long after the advisor's
  intervention window.

V54 and v54a are rejected. The repair excludes
`prioritize-intervention` definitions from generic grounding; such a scheme
now enters credit only when its own advisor selected the action. A structural
test requires no inherited component on the first post-cap generic action.
Do not rerun these ranks: the held-out pragmatic falsifier already failed.

Protocol: `references/INHERITED_SCHEME_PROTOCOL.md`.

## Rejected experiment: v55 competing paired terminal relations

Parent: accepted v49b `candidate-6ee87ced5a667cae`.

Preregistered hypothesis:

- a sparse, highly fragmented visual field can ground a content-free
  `paired-marker-coverage` terminal relation for an evidenced controlled pair;
- search the learned joint topology for a state maximizing coverage for both
  members and compete that plan with object contact through either
  shortest-grounded or marker-first arbitration;
- every selected step must predict and then reduce distance to its grounded
  target. Recoloring and action permutation must preserve the structural plan;
- advance `m0r0` beyond level 1 within 400 actions, or reject the relation as a
  goal even if its transition predictions pass.

Result:

- the exact-off contact-only control reproduced accepted v49b at 1/6 levels
  and `[20, 380]`;
- shortest-grounded and marker-first both grounded two terminal candidates,
  selected the 208-cell sparse field, and repeatedly executed the same
  ten-step plan;
- in each same-level retry, the operative stream recorded 54 exact distance
  reductions and five terminal-step prediction failures, but neither
  descendant advanced beyond 1/6 levels or improved score;
- the plan length decreased from ten to one and then reset to ten. Thus sparse
  marker coverage was a predictable intermediate trigger that displaced the
  pair, not a terminal goal.

V55 is rejected. The next accommodation must preserve the learned marker
transport while falsifying that particular grounded target as terminal, then
seek a different relation or phase. Do not grant more plan depth and do not
credit the 54 intermediate predictions as pragmatic goal evidence.

V55a accommodation result:

- on the first terminal-step displacement, the offspring retained the sparse
  marker relation but retired the exact ordered target binding;
- it then generated a distinct assignment with an eleven-step plan, proving
  that accommodation changed the grounded structure rather than merely
  restarting the same target;
- the alternative route necessarily crossed the first transport trigger. It
  therefore reset before reaching the new target, repeated the eleven-step
  route, and again finished at 1/6 levels with `[20, 380]`;
- only one target was correctly retired; the later four prediction failures
  occurred before the alternative terminal state and therefore did not
  license retiring it.

V55a is rejected. Its failure preregisters the next recombination: the marker
goal planner must consume confirmed v50 context-dependent transitions so that
the trigger is represented as a portal edge during search. Compare that
offspring with source-matched contact-only and contextual-contact controls.

V55b recombination result:

- four source-matched offspring tested contact-only, contextual-contact,
  contextual-marker, and contextual-plus-transport marker planning;
- all four remained at 1/6 `m0r0` levels and `[20, 380]`;
- contextual-marker confirmed two context-dependent edges, consumed them in
  90 bounded successor evaluations, retired three distinct marker bindings,
  and still produced no progress;
- the transport variant additionally induced the convergent transport family
  and invoked it 5,436 times across internal search expansions before falling
  back to contact planning. This count is a search diagnostic, not an
  environment-action or intelligence metric;
- exact-off and contextual-contact controls reproduced their prior outcomes.

V55b is rejected. This closes the local “unconnected modules” explanation:
goal search did consume the learned transition model and generated structural
variation. Marker activation remains an intermediate operation in a missing
multi-phase procedure, not a sufficient goal. Stop adding `m0r0` planning
depth or isolated terminal predicates. A future return must preregister a
phase/procedure discriminator learned from progress, not another target
ranking.

## Rejected experiment: v56 paired occlusion procedures

Parent: accepted v49b `candidate-6ee87ced5a667cae`.

Preregistered hypothesis:

- treat loss and later recovery of the grounded pair during an evidenced plan
  as a temporally extended option rather than a one-frame transition;
- compare exact-off, repeat-entry, reuse-the-prior-progress-action, and
  canonical-probe continuations;
- confirm a macro only after the same entry, continuation, and recovered pair
  outcome occurs twice, quarantine conflicts, and expose planner use;
- require progress beyond `m0r0` level 1 within the same 400-action budget.

Result:

- all four source-matched offspring exactly matched at 1/6 levels,
  `4.7619047619` for the target game, and `[20, 380]`;
- the prior level's progress-associated action was retained, so the
  cross-level credit path was available;
- nevertheless every procedure variant recorded zero occlusion proposals,
  confirmations, conflicts, learned macros, and planner uses;
- the operative pair planner instead completed the same 64-trial budget and
  ended with `joint-plan-step-observed`.

V56 is rejected. This is not evidence against temporally extended options.
More importantly, a direct parse of the immutable recording corrected the
visual diagnosis that motivated it. Across the relevant transition, both
members remain exact 4-by-4 objects with the grounded signature; one action
maps the pair discontinuously from lower anchors back to the upper region.
V50's contextual portal edge already represented that transition. V56
therefore tested an event that does not occur, rather than exposing a missing
occlusion detector. Do not widen its trigger. Future event hypotheses must be
derived programmatically from recordings and preregister their expected event
indices before a policy mutation is implemented.

## Completed experimental branch: v26

- Preregistered causal hypotheses and typed predictive/pragmatic structural
  credit are implemented.
- Successful procedures are first-class scheme inputs with bounded prefix,
  suffix, interleaving, and role-binding variation.
- Pragmatic stagnation triggers variation; composite applications receive
  component-specific falsification.
- The full v26d run preserved eight levels and increased score slightly, but
  the gain came only from successful role replay. V26e and v26f improved
  trace-level inhibition without task gain. None is promoted.

## Next actions

1. Preserve accepted v49b. V50-v56 now show that dynamics, portal
   accommodation, terminal variation, actual planner composition, and a
   nonexistent pair-absence procedure hypothesis are insufficient on `m0r0`
   level 2. Pause that chain until a cross-game progress-grounded event and
   procedure learner exists.
2. Build a content-addressed inherited scheme substrate. Keep immutable typed
   scheme definitions separate from an append-only evidence ledger; offspring
   inherit only hashes whose predictive, information-efficiency, and pragmatic
   evidence clears preregistered thresholds.
3. Train that substrate with isolated multi-game curricula and rotating
   held-out folds. Share definitions, counterexamples, transition-equivalence
   classes, and calibration—not action routes, coordinates, colors, or game
   identifiers.
4. For `g50t`, learn an explicit gate-phase experiment or switch targets; the
   v43c-v43f and integrated-Gemma runs all preserved level 1 but added no level
   2.
5. Route qualitative frame difference and flow into causal policy only through
   typed, bounded advisors; passive perception alone is not task credit.
6. Evaluate diverse operators in isolated populations across games; require a
   new level or material efficiency gain from each operative trait.
7. Run source-matched target ablations and the full 25-game gate only for a
   qualifying offspring; keep v49b accepted otherwise.
8. Prepare the first real Kaggle notebook submission as an explicit external
   action. Report its public score and submission status separately; private
   score remains unavailable until Kaggle exposes it.

## Preregistered experiment: v57 repeated-form effect events

Status: implementation and structural tests complete; no task result yet.

The development-only recording audit defines a content-addressed event without
game identity, color, absolute position, or action constants:

`same repeated-form subject + same action + supported prior effect -> different effect`

It normalizes exact repeated objects by shape and arity and their member
displacements by common scale. An expectation becomes eligible only after two
matching prior effects. The accepted `m0r0` recording yielded 354 supported
predictions, 334 confirmations, and 20 deviations.

The first v57 population exposed an invalid action abstraction. Its history key
used only the API action ID, conflating every coordinate-bearing action-6
click. `confirm-affordance` replayed 135 actions on `lp85` and regressed from
three levels to one. `confirm-discontinuity` replayed 338, regressed `lp85` to
one level, and lost `g50t` level 1. A confirmation could also generate another
confirmation recursively. Both variants are rejected. `phase-segment` exactly
matched the control at four total levels and score 6.6465283447 across the two
games, so it supplied no gain.

V57a grounds a parameterized action by the selected object's structural role,
abstains when the coordinate has no structural binding, and prevents the
immediate confirmation result from scheduling another confirmation. With this
correction, five independent held-out recordings yield 913/913 confirmations
and zero deviations. The previously reported ten `lp85` action-6 deviations
disappear; they were artifacts of action-ID conflation.

V57a real result:

- exact-off: 4 levels, score 6.6465283447;
- confirm-affordance: 4 levels, score 4.0072549883; `lp85` level 2 slowed from
  8 to 85 actions;
- confirm-discontinuity: 2 levels, score 0.3302558292; lost `g50t` level 1 and
  one `lp85` level;
- phase-segment: 4 levels, score 6.6465283447, exactly matching control despite
  14 maximum in-level detections on `g50t` and 22 on `lp85`.

All v57a variants are rejected. Exact replay is not a safe generic
confirmation for toggling or consumptive actions, and a phase suffix adds
nothing when the raw frame key already distinguishes the states.

## Preregistered experiment: v58 parameterized affordance propagation

Parent: accepted v49b. Donor insight: rejected role-grounded v57a.

When a supported no-effect structural action role produces a nonzero repeated-
form effect, preserve that newly evidenced role but do not repeat the concrete
action. Instead, allow exactly one untried concrete token with the same
object-relative `ActionRole` in the current state. This is a bounded
select/parameterize/apply variation:

`newly effective role(target₁) -> try same role(target₂), target₂ untried`

The operator must abstain if the action has no structural grounding or no
distinct equivalent token. It must never select the triggering token as its
variation.

Falsifier: reject if the advisor is inert, if it merely reproduces an already
selected base action, if it loses any control level, or if it does not add a
level or materially improve action efficiency. Develop first on the identical
`lp85`/`g50t` pair, with exact-off and v57a phase-segment controls.

V58 result: the parameterized advisor fired four times on `lp85`, preserved all
four control levels, and exactly matched the 6.6465283447 two-game score.
However, it slowed `lp85` level 2 from 8 to 10 actions. Trace inspection showed
four consecutive alternating variations: each varied action's response
scheduled another variation. This violated the intended one-variation causal
scope, so v58 is rejected.

V58a adds a causal guard: the observation caused by the one varied action may
update the effect model but cannot schedule another propagation. Rerun the
identical three-way control/phase/propagation population.

V58a result: two noncascading variations remained, all four levels and the
6.6465283447 score were preserved, but `lp85` still changed from
`[37,8,54,301]` to `[37,10,54,299]`. Both variations preempted an active
cyclic-alignment procedure.

V58b changes only arbitration: grounded repair/replay, select-apply-commit,
cyclic alignment, paired planning, committed trajectory, shape translation,
productive reuse, relational schemes, parameterized schemes, and inherited
schemes all retain priority. Affordance propagation runs only after those
advisors abstain and before generic action-family exploration. Falsifier and
development games remain unchanged.

V58b result: exact control trajectories and score were restored, but
propagation selected zero actions despite 14 maximum in-level `g50t`
detections and 48 on `lp85`. It is rejected as behaviorally inert.

## Preregistered experiment: v59 disequilibrium-gated reflection

Parent: accepted v49b. Donor: rejected v58b.

Preserve the grounded advisor hierarchy during ordinary execution. If the
mind signals pragmatic disequilibrium, allow one pending, role-grounded,
noncascading affordance variation to preempt the stalled scheme. Require a
distinct untried equivalent token. Thus the arbitration rule becomes:

`supported base scheme while progressing`
`-> pragmatic stall`
`-> one reflected role variation`
`-> observe without cascade`

Falsifier: the mutation must be operative only after disequilibrium, preserve
all control completions and completed-level action counts, and add a level or
materially reduce stalled-level waste. Otherwise reject it. Use the identical
`lp85`/`g50t` source-matched development pair first.

V59 result: exact control trajectories and 6.6465283447 score were preserved;
zero variations were selected. The three `lp85` newly-affordant events arose
at 4–6 no-progress steps while cyclic alignment was still productive. The
level advanced before the eight-step disequilibrium threshold and reset the
pending events. No newly-affordant event appeared on the stalled level. V59 is
rejected as non-qualifying, and the immediate repeated-form event policy branch
is closed. Do not tune the threshold downward to force activity.

Next: retain the content-addressed event definition and corrected action-role
binding in the development substrate. Build the append-only cross-offspring
evidence ledger and acceptance gate so predictive definitions can be inherited
without automatically becoming action advisors. Runtime activation must be a
separate, credit-bearing mutation.

## Accepted development artifact: common-sense snapshot v1

This is a cultural knowledge artifact, not a promoted task agent.

- Definition: `stable-repeated-form-action-effect`, operator
  `observe-event`.
- Confirmations: 2,047.
- Falsifications/counterexamples: 20.
- Held-out confirmations: 1,713.
- Contributing agent provenances: 3.
- Prediction error: 0.9675858732%.
- Library root:
  `64afd8c3e44b1af4fe387fc9f5f04bf8ab95b1229cb3bba51263fa6ca68b62d0`.
- Evidence-ledger root:
  `21d454b314d52e6288eef085a364adb526e8a779834e254dbca8bac95a6d88eb`.
- Combined common-sense root:
  `b342e83f2bb14b134f8febf1b203c208ee74193b0bf0d07bc3796fc8df329a78`.
- Evidence report:
  `reports/common-sense-v1-repeated-form-effect.json`.

The predictive gate requires at least 100 confirmations, 100 held-out
confirmations, two held-out partitions, two agent contributors, at most 10%
falsification, and zero regressions. Unlike the pragmatic scheme gate, it does
not require level progress. Observation-only definitions are excluded from
runtime action attribution and intervention selection.

Next breed v60 from accepted v49b with this exact immutable library. Its
source-matched control test must prove that knowledge inheritance alone
preserves behavior. V60 cannot replace v49b without an independently promoted,
task-improving runtime use of the definition.

V60 result:

- candidate `candidate-d1ef98414f250899`;
- five-game score 8.6109922903, exactly matching its source control;
- ten levels with identical vectors:
  `ar25 [17,17,366]`, `g50t [27,373]`,
  `lp85 [37,8,54,301]`, `m0r0 [20,380]`,
  `sb26 [9,15,15,361]`;
- one inherited observation-only definition in every process;
- zero inherited action selections or operative action attribution;
- exact library, evidence, and combined roots present in `MindConfig`;
- Kaggle export succeeded and network-disabled smoke passed;
- 234 tests passed, 3 skipped; Ruff and mypy passed.

V60 is accepted as a development/cultural offspring but does not replace v49b
as the task-performance champion. The next generation may use its definition
only through a separately preregistered policy mutation with pragmatic credit.

The source-matched population has four frozen modes:

- `off`: accepted behavior;
- `confirm-affordance`: replay once only when supported no-effect becomes
  nonzero;
- `confirm-discontinuity`: replay once after any supported nonzero contextual
  change;
- `phase-segment`: do not replay; split the causal-state key after a supported
  deviation.

Falsifier: a mode is rejected if its detector remains inert, if it adds
replays without a new level or material efficiency gain, or if it regresses an
accepted level. Recording prediction accuracy alone cannot promote it.

Only a qualifying v58 variant proceeds to `ar25`, `m0r0`, `sb26`,
deterministic rerun, and the full suite.

## Rejected experiments: v61-v64 proposal-coverage probes

Parent: accepted v49b `candidate-6ee87ced5a667cae`.

V61 tested one deterministic frame-center click before the accepted explorer:

- candidate `candidate-5a85e3b0db5395d9`;
- five-game score 14.4856728742 with the same seven levels as v49b;
- it delayed the accepted first completion by one action on `ft09`, `lf52`,
  and `m0r0`, while `bp35` and `cn04` remained at zero;
- rejected because an ungrounded first contact added no level and weakened
  accepted efficiency.

V62 tested a deeper retry cap for already productive action roles:

- candidate `candidate-d0a0255c3cac4c49`;
- `sp80` regressed from accepted level 1 at action 196 to zero levels in 400
  actions;
- 28 productive-reuse selections supplied repetition but not the missing
  procedure;
- rejected because more exploitation of a responsive action family was
  actively harmful.

V64 grafted the independently successful research object/frame graph into the
shared runtime path:

- candidate `candidate-51cd888f4c2b9a6e`;
- after one failed coordinate-only retry, it replaced the click vocabulary
  with compact monochrome components and normalized dominated edge strips in
  the graph state;
- `vc33` advanced from zero to level 1 at action 262, exactly twice, with
  `[262,138]`, seven resets, and 254 compact-frontier selections;
- the eleven-game accepted-progress gate preserved nine accepted action
  vectors and added `vc33`, but regressed `tn36` from level 1 at action 123 to
  zero levels;
- rejected despite the deterministic gain because the preservation gate is
  absolute.

The counterexample localizes the missing trigger. On recorded post-failure
frames, `vc33` had 10-15 compact proposals for 10-15 perceptual objects, while
`tn36` had 87-88 compact proposals for about 42-48 objects. The graph
abstraction was compressive only on the gain. The next offspring may activate
the branch only when its symbolic proposal vocabulary does not exceed the
current perceptual object vocabulary; no game identity, coordinate, or known
solution may enter that gate.

Evidence:

- `reports/experimental-v61-center-probe-five-400.json`;
- `reports/experimental-v62-sp80-deep-reuse-r1-400.json`;
- `reports/experimental-v64-vc33-compact-frontier-r1-400.json`;
- `reports/experimental-v64-vc33-compact-frontier-r2-400.json`;
- `reports/official-isolated-v64-progress-gate-400.json`.

## Accepted experiment: v64b compressive component frontier

Parent: accepted v49b `candidate-6ee87ced5a667cae`. Donor evidence:
rejected v64 `candidate-51cd888f4c2b9a6e`.

Preregistered repair:

- retain the failed-coordinate-only trigger;
- derive connected monochrome component clicks and an edge-strip-normalized
  frame state without game identifiers or fixed coordinates;
- activate that ontology for one retry only when it is nonempty and has no
  more proposals than the current `SceneTracker` object set;
- latch the ontology for the retry so action tokens and graph state cannot
  flicker, and clear graph bookkeeping if the latched mode changes between
  retries;
- retain higher-priority grounded advisors, including productive-role reuse.

Falsifying comparison:

- ungated v64 produced 87-88 compact candidates for roughly 42-48 perceived
  `tn36` objects, replaced the accepted post-failure vocabulary, and lost its
  level-1 completion;
- v64b diagnosed that vocabulary as
  `expands-perceptual-ontology`, selected it zero times, and restored the exact
  accepted `[123,277]` vector twice;
- `vc33` produced 10-15 compact candidates for 10-15 perceived objects,
  diagnosed `compressive-component-vocabulary`, and retained `[262,138]`
  exactly twice.

Promotion evidence:

- candidate `candidate-fdd57b632dca6219`;
- paired deterministic runs: two levels total, exact `tn36 [123,277]` and
  `vc33 [262,138]`;
- eleven-game gate: 20 levels, every v49b completed-level action vector
  preserved, and `vc33` added;
- process-isolated 25-game score:
  `4.640274445854323/100`, 20/183 levels across 11 games, 0/25 complete games,
  25/25 coverage, and 10,000 actions;
- the only completed-level delta from v49b is `vc33` level 1 at action 262;
- 240 tests passed and 3 skipped; Ruff and mypy passed;
- the exact candidate exported without translation and the network-disabled
  Kaggle smoke passed.

Frozen evidence:

- inference commit:
  `f19624c63e303292ab1691e2e2cb66689922a61e`;
- candidate inference fingerprint:
  `198544527a6a56f95fd2f112c3a9327ecbf4e0e13eacefbda89b50a7b84836dc`;
- candidate SHA-256:
  `3584b72aac89d51ac29bfe7e0084f77ef4a58f649c098bd1d7e13b31cd43e218`;
- full report SHA-256:
  `3a33e4b6322230964357a9889d31e42c2acb507189ae69ac10c9e6ebf8aa7fe3`;
- export overlay SHA-256:
  `3c38a46492c1322372c0b972a266c0585772891185295e1b9fb883d2554c0f51`;
- export notebook SHA-256:
  `db385cdb59258497efda2ff844be0388535a881833b9564f0b41c7c468c30371`.

Reports:

- `reports/experimental-v64b-tn36-vc33-r1-400.json`;
- `reports/experimental-v64b-tn36-vc33-r2-400.json`;
- `reports/official-isolated-v64b-progress-gate-400.json`;
- `reports/official-isolated-v64b-public-400.json`.

V64b replaces v49b as the task-performance champion. The gain is narrow but
causal: a graph-control result transferred into the shared runtime only after
its proposal language was constrained to be an actual abstraction rather than
an expansion.

## Accepted experiment: v65b bounded connector-graph synthesis

Parent: accepted v64b `candidate-fdd57b632dca6219`.

Disequilibrium:

- the accepted select/apply/commit family solved the first three `sb26`
  levels, then treated a repeated reference-interior shadow as a flat legacy
  program and exhausted 361 actions;
- the visible scene contained enough relational structure to describe a
  connector assignment, but the runtime had no bounded language for ordered
  references, nested containers, fixed payloads, external connector
  inventory, and cyclic reuse in one program;
- a generic repair had to abstain whenever the graph was ambiguous,
  nonexhaustive, shape-inconsistent, or merely competed with an independently
  grounded legacy program.

Mechanism and safety boundary:

- derive actual object references and wrappers from color, normalized shape,
  dimensions, adjacency, containment, and visible connector inventory;
- enumerate bounded root assignments and accept exactly one minimum-cost
  exhaustive graph program;
- require every alternative root to be a definitive no-solution, rejecting a
  unique-plus-ambiguous mixture;
- reject acyclic prefixes that leave required structure unused; truncate only
  after an evidenced productive cycle;
- use the graph as a fallback when no legacy structural program exists, or
  allow it to dominate only the narrow repeated-reference-interior shadow
  whose actual adjacent graph segments support the same grounding;
- include no game ID, fixed coordinate, color constant, action ID, or known
  solution.

Promotion evidence:

- candidate `candidate-34708ca0a3fb4129`;
- inference fingerprint
  `88950d0b02c3eb2aa959ef44c9f2b094c2ccdddf6edb36e1b85f040895418151`;
- two frozen process-isolated target repeats completed `sb26` 8/8 at 124
  actions with identical level actions
  `[9, 15, 15, 15, 17, 19, 17, 17]`;
- the eleven-game preservation gate retained every non-target score, level,
  action total, and completed-level action vector exactly while replacing
  `sb26 [9,15,15,361,0,0,0,0]` with the complete vector;
- the process-isolated full public-development suite reached
  `7.973607779187656/100`, 25/183 levels across 11 games, 1/25 complete games,
  25/25 coverage, and 9,724 actions;
- relative to v64b, the only per-game behavioral delta is `sb26`; score rose
  from `4.640274445854323`, levels from 20/183, complete games from 0/25, and
  actions fell from 10,000;
- adversarial controls reject color-only and shape-only false matches,
  nonexhaustive acyclic prefixes, ambiguous roots, and mixed
  unique-plus-ambiguous roots;
- 271 tests passed and 3 skipped; Ruff and mypy passed;
- both network-disabled Kaggle smoke paths passed, the exact candidate
  exported without translation, and the technical prize audit passed;
- the private, internet-disabled notebook
  `pauloabelha/reflector-arc-agi-3-v65b` version 1 completed on Kaggle and
  emitted `submission.parquet`; submission `55113224` was accepted at
  2026-07-30T15:36:04.110000Z and its hidden rerun is pending. No public or
  private Kaggle score has returned. Public competition publication,
  participant-owned repository confirmation, and eligibility evidence remain
  manual.

Frozen evidence:

- inference commit:
  `ad68c9cd4c4915cbc220c25fba9998425ba5abd9`;
- candidate SHA-256:
  `19e2e4a399954453690d27e9d678177bc507e1f788bbdd63a60470570a18a26f`;
- full report SHA-256:
  `f765fc20ff7fe33342d3015859aff8bb60308a316b66ffada7c71768363ee042`;
- target report SHA-256 values:
  `cced81bd2b6839484152caca94cd91397cbac810187727467da645e22e8cea6e`
  and
  `5503b263677056e1b3a05fbf95c401c1d7f217888eb60f771d2e188ef5a65e24`;
- preservation report SHA-256:
  `efc41c2ef2b664c2ecc20abfa47c323775dbbfa1678f805d2dae7a24ebc10fe3`;
- export overlay SHA-256:
  `cb7f8a8a66c2766ce0a448ee383df7f5e02b8d0c38d23afcd7b19aebe3790285`;
- export notebook SHA-256:
  `5b27e2c59d511f5fd74fa036af4d4eef24d9407aca25ffeb12f0b61c8b3fd989`.

Reports:

- `reports/official-isolated-v65b-sb26-r1-400.json`;
- `reports/official-isolated-v65b-sb26-r2-400.json`;
- `reports/official-isolated-v65b-progress-gate-400.json`;
- `reports/official-isolated-v65b-public-400.json`.

V65b replaces v64b as the task-performance champion. It is a substantial
known-public gain and the first complete game, not hidden-transfer evidence.
The exact export has entered Kaggle hidden evaluation as submission
`55113224`; use `references/KAGGLE_ARC3_SUBMISSION.md` and keep the pending
submission, local score, Kaggle public score, and Kaggle private score
separate.

## Accepted experiment: v66 learned lattice effects and exact CSP

Parent: accepted v65b `candidate-34708ca0a3fb4129`.

Disequilibrium:

- v65b preserved the first five `ft09` completions exactly but exhausted the
  remaining 265 actions on level 6;
- the retained local relation vocabulary could interpret the visible clues,
  but the runtime lacked a learned actuator-effect model and a global inverse
  planner over the repeated lattice;
- exact action centroids were not stable intervention groundings, so clicks
  had to bind generically to a unique actuator region.

Mechanism and safety boundary:

- ground exactly one regular lattice of repeated dense, non-solid square
  actuator forms with visible relation clues;
- canonicalize a click only when exactly one node region contains it;
- induce a binary relative effect law from at least two normalized,
  structurally distinct node-neighborhood contexts;
- validate every successor prospectively and quarantine the lattice for the
  level on any mismatch, including an unexpected no-op;
- reject unknown clue symbols, mixed forms, ambiguous groundings, unstable
  membership, inconsistent cycles, or unrepresented planned actions;
- solve the visible equality/inequality system with an exact CSP bounded to
  64 clicks and 100,000 search nodes;
- include no game ID, coordinate, color, literal action ID, direction, or
  known route.

Promotion evidence:

- candidate `candidate-c9825fedf72a2a32`;
- inference fingerprint
  `e7319dd72e4c3060951d0061a671d704be04052584c3737f86699a01d3e29b49`;
- two frozen process-isolated target repeats completed `ft09` 6/6 at 162
  actions with identical level actions `[4,7,14,16,94,27]`, score
  `99.00375088921943`, and 11 lattice-planned actions;
- the eleven-game preservation gate retained every non-target score, level,
  action total, and completed-level action vector exactly;
- the process-isolated full public-development suite reached
  `9.287893493473371/100`, 26/183 levels across 11 games, 2/25 complete games,
  25/25 coverage, and 9,486 actions;
- relative to v65b, only `ft09` changes; score increases by
  `1.314285714285715`, levels by one, complete games by one, and actions fall
  by 238;
- 282 tests passed and 3 skipped; Ruff and mypy passed;
- both network-disabled Kaggle smoke paths passed, exact export passed, and
  the technical prize audit passed;
- v66 has not been submitted to Kaggle; pending submission `55113224` is the
  earlier frozen v65b notebook and must remain attributed to v65b.

Frozen evidence:

- inference commit:
  `b6f9ba4476d19c3bea99acce1aa3a75c332e9678`;
- candidate SHA-256:
  `eeca3f9f3d4115ed280348d906680543bf8c53c3eaddf38f8bdb7f7676d27c00`;
- full report SHA-256:
  `aa5a77a95fe4178e3c2a463caf40d0a611f71e7eb75b10272b42b2b3f7f32de3`;
- target report SHA-256 values:
  `d3f80c529bc60a9fd457a9e0f0c944b5d50430fc0eb55c8bd430d82ce28ad540`
  and
  `4fb4a64be5d9aabe0256d416b9b3cbb7af80b72e740fa73aae639b55490ab34d`;
- preservation report SHA-256:
  `d0d195099332da3be20244a2b74ebad45219014ea74d8843899ce134f4009b68`;
- export overlay SHA-256:
  `7f44f6ca6a6ee9b8deeac39610975e747c370bdf3c8ce02957c1d9e66b7dd2ef`;
- export notebook SHA-256:
  `bb2a69f46ad78fc98915506f2f815223c7132edfa2c93a1b3a255c9c7b9de1d0`.

Reports:

- `reports/official-isolated-v66-ft09-r1-400.json`;
- `reports/official-isolated-v66-ft09-r2-400.json`;
- `reports/official-isolated-v66-progress-gate-400.json`;
- `reports/official-isolated-v66-public-400.json`.

V66 replaces v65b as the local task-performance champion. It is a narrow,
causally isolated known-public gain and the second complete game, not hidden
transfer evidence.

## Accepted experiment: v67 segmented permutation transport

Parent: accepted v66 `candidate-c9825fedf72a2a32`.

Hypothesis:

- when a conserved same-form token domain changes by one unique equal-pitch
  segmented permutation, retain that effect only provisionally;
- register the full-domain prediction before a subsequent same-form
  controller intervention and promote only after an exact rendered successor
  match;
- bind confirmed generator identities back to currently represented
  controller forms and run bounded exact marker transport over the projected
  token-color state;
- reject ambiguity, same-transition promotion, domain drift, prediction
  conflict, unsupported effects, and unrepresented plan steps.

Result:

- frozen source/candidate commit
  `509575e88cff60d33368006ca77b6eb30db67a40`;
- candidate `candidate-a1ccbdb17d674b78`;
- inference fingerprint
  `fa8781903bfbe765a67d7839d28089213b43a585a84ca8188309ec4e6f2794e9`;
- two frozen `lp85` repeats exactly reached 4/8 levels, score
  `10.285890058914008`, level-action vector
  `[37,8,54,71,230,0,0,0]`, 400 actions, and zero resets;
- the archived cognition stream shows the level-4 plan beginning after 58
  exploratory actions with eight same-form confirmations, three represented
  effects, and zero conflicts; it explores 651 projected states and completes
  in 13 planned actions at level action 71;
- the eleven-game gate scored `21.16014538889156/100`, reached 27 levels, and
  preserved every non-`lp85` v66 outcome exactly;
- the full process-isolated suite scored `9.310463971112286/100`, reached
  27/183 levels across 11 games, retained two complete games and 9,486 total
  actions, and changed only `lp85`;
- relative to v66, score increases by `0.022570477638915065` and levels by
  one, with no change in complete games, progress games, or total actions;
- 313 tests passed and 3 skipped; Ruff and mypy passed;
- exact export, both network-disabled smoke paths, and the technical prize
  audit passed;
- v67 has not been submitted to Kaggle; live status still reports v65b
  submission `55113224` as `PENDING`.

Audit limitation:

- the frozen candidate rationale says “distinct equivalent controller,” but
  the runtime does not compare controller centroids; a repeated controller
  can supply the preregistered confirmation;
- v67 is therefore prospective but not structurally held out. A source-matched
  distinct-controller gate must be tested before claiming that stronger
  evidence boundary;
- the 12 observations, eight confirmations, three represented effects, zero
  conflicts, 651 search states, and 13 plan steps are preserved in the
  archived cognition stream. Terminal scorecards reset the detailed counters
  after progress, though they retain all 13 decision reasons.

Frozen evidence:

- candidate SHA-256:
  `80e90a68142ee31eebc743c4eb3fa0f30c31b7b531e9d348b8f936e9216b911a`;
- target report SHA-256 values:
  `df27742d92b09faf3b2852e59b1fcf5a24e202e367211e72d13966c5d22018f7`
  and
  `21ede94cf45b9a2aea93a86b3495f3bc972f13f3ad9f88f8b2a74f9bce63040c`;
- preservation report SHA-256:
  `7a83fa2ec26dda1d2b1d5a113c36e5db5f7642ab95c35108869ff32e3ccfb949`;
- full report SHA-256:
  `e938f460d3f100b52a11ac652b80e63c4cf184ecbaf9d5fdfce54a6fb1e6d69d`;
- export overlay SHA-256:
  `b6dc044439077ea6d01f6021791c659ee84ab9b8731e932a9454ddd03b88ef8f`;
- export notebook SHA-256:
  `1e8a4d916eb46f30242789db7797aac19b3eb19340e3f641e76218d4dde930bf`.
- archived v67 cognition JSONL gzip SHA-256:
  `93da482f144a4effddb80ea94e2a09a6fb320d69fd2e4e60e9aa1cf6e44b9898`.

Reports:

- `reports/official-isolated-v67-lp85-r1-400.json`;
- `reports/official-isolated-v67-lp85-r2-400.json`;
- `reports/official-isolated-v67-progress-gate-400.json`;
- `reports/official-isolated-v67-public-400.json`.
- `reports/official-isolated-v67-lp85-cognitive.jsonl.gz`.

V67 replaces v66 as the local task-performance champion. The mechanism is
generic and prospectively grounded, but the gain is one known-public level
and is not hidden-transfer evidence.

The requested K-line work has completed its first, behaviorally isolated
substrate: `reflector/core/kline_memory.py` now provides immutable
content-addressed definitions, explicit registered-generator dispositions,
separate evidence identities, collision-checked snapshot roots, sparse
partial-cue postings, deterministic bounded ranking, hard
precondition/contradiction abstention, and an optional exact structural
matcher. Cue overlap alone cannot claim grounding and retrieval exposes no
action or executable payload. Focused tests pass, but this module is not in
`MindConfig`, exploration, policy, or the Kaggle overlay and therefore is not
part of accepted v67 inference. Runtime integration remains exact-off until
cue compilation, structural grounding, scheduler fairness, and held-out
retrieval evidence pass the gates in
`references/KLINE_SYMBOLIC_MEMORY.md`.

## Accepted experiment: v68 path-cycle transport

Candidate: `candidate-35de85c4fe395c3a`

Frozen source/candidate commit:
`59daf6171026b986c1e26aaa5fa1f56e2ef03269`

Mechanism:

- infer exact one-step rotations over bounded contiguous intervals of one
  conserved uniform simple rectilinear slot path;
- bind visually identical controllers through local endpoint, straight, or
  corner topology plus normalized distance context;
- retain v67's prospective exact-successor confirmation and bounded projected
  marker transport;
- expose cumulative observations, predictions, confirmations, conflicts,
  candidate counts, controller context, and plan-step diagnostics.

Evidence:

- two frozen target runs exactly reproduce
  `[37,8,54,71,50,180,0,0]`, five `lp85` levels, and
  `19.624778947802895`;
- the frozen eleven-game gate changes only `lp85`, rising from
  `21.16014538889156` to `22.00913528788146`;
- the 25-game result is `9.684019526667843/100`, 28/183 levels across
  11 games, two complete games, and 9,486 actions;
- level 6 reports `domain-unrepresented`: its 75 matching slots exceed the
  fixed 64-slot bound and are deliberately not forced into the representation;
- 341 tests pass with three skipped, Ruff and mypy pass, exact export passes,
  and both network-disabled smoke paths pass.

V68 replaces v67 as the local task-performance champion. The gain is one
known-public level and is not hidden-transfer evidence.

## Accepted experiment: v69 primary colored-stencil composition

Candidate: `candidate-2336bc12a0bc28de`

Frozen source/candidate commit:
`2f3020804baf7578ff691ace2fa556783eb3735a`

Mechanism:

- uniquely ground one congruent reference/construction grid pair, visible
  palette roles, and one outlined movable template from the rendered frame;
- bind movement controls only from observed pose translations and identify the
  remaining represented plain control as submit after four movement bindings;
- search a bounded exact last-write-wins program over palette selection,
  eight-pose navigation, and normalized primary half-plane overwrites;
- retain no game identity, fixed color, coordinate, action mapping, or route.

Evidence:

- two frozen `cd82` repeats exactly reached 2/6 levels at
  `[12,6,382,0,0,0]`;
- the twelve-game gate preserved every non-`cd82` accepted trajectory;
- the process-isolated 25-game suite scored
  `10.255448098096416/100`, reached 30/183 levels across 12 games, retained
  two complete games, covered 25/25 games, and used 9,486 actions;
- relative to v68, only `cd82` changes, adding two levels and
  `0.571428571428573` score.

V69 replaces v68 as the accepted local public-development champion. This is a
causally isolated gain on a known public game, not hidden-transfer evidence.

## Immediate continuation toward 20/100

The clean restart independently reproduced v74 in one fresh process per game:
`14.450686193334509/100`, 35/183 levels, three complete games, 25/25
coverage, and 9,185 actions. The raw report is
`reports/official-isolated-v74-clean-baseline-400.json`.

The first new branch is **v75 action-conditioned translation algebra**.
Cross-game trace clustering found that exact-frame novelty dominates every
zero-progress game even though plain actions repeatedly cause stable relative
translations. The bounded compiler in
`reflector/core/action_translation_algebra.py`:

- proposes a relative action law from one rendered transition but grants no
  authority from that row;
- preregisters the displacement on a later structurally distinct source;
- retains only action identity plus relative displacement, never game, color,
  coordinate, route, or frame identity;
- preserves contextual no-ops as collision evidence and quarantines a
  contradictory nonzero effect;
- omits oversized substrate components rather than raising the task-object
  bound, while retaining hard frame, object, action, and provenance caps.

The chronological v74 audit gives prospective authority on 13/25 games and
same-episode inverse pairs on 7/25. `ls20` and `re86` repeatedly form complete
four-direction algebras; `tu93` forms a safe inverse pair; `dc22` remains
partial. This is representation evidence, not task progress. The immutable
audit is `reports/v75-action-translation-audit-v1.json`; its complete input
recordings and cognitive streams are compressed beside it.

The exact-off runtime integration is now complete behind
`enable_action_translation_algebra`. Generation-35 trace-only offspring
`candidate-7774a464a9ee9f95` ran `dc22`, `ls20`, `re86`, and `tu93` in fresh
processes. Every 400-action vector exactly matched v74 while the live
cognitive streams gained prospective authority on all four games. This
validates runtime observability and behavioral isolation only; it is not a
score gain.

The first operative child, v76 `candidate-b584013b761549e7`, traversed
authoritative inverse generators in bounded straight rays. It was selected
198 times on `dc22`, 320 on `ls20`, 305 on `re86`, and 8 on `tu93`, but all
four games remained at zero levels. This falsifies undirected generator-ray
coverage as a useful quotient. V76 is rejected without preservation or a full
suite; the feature remains exact-off by default.

V77 `candidate-f1554519f6c31f32` narrowed the claim to novel relative contact
events and limited each authoritative generator to one ray per episode. It
issued 4/6/16/3 contact-affordance probes on `dc22`/`ls20`/`re86`/`tu93`,
respectively, but every game remained at zero levels. It also exposed a
partial-identification flaw: an unlearned generator can temporarily appear to
be a non-generator affordance. V77 is rejected.

V78 `candidate-927ca35ac9ce29e2` returns directly to accepted v74 as a
trace-only positive action-effect typer. It never infers a type from absence.
The clean-v74 audit gains authority on 17/25 games and non-translation
authority on 14/25. A six-game live run exactly preserved every v74 action
sequence while exposing discriminative type signatures on `g50t` and `tu93`,
one non-discriminative shared signature on `re86`, and a safe component-cap
failure on `m0r0`. This is a valid representational substrate, not task
progress.

V79 `candidate-1dcd58cc020f3fe0` required complete positive typing and at least
two action signatures, then balanced at most 64 selections per episode across
effect families. Across `cn04`, `dc22`, `ls20`, `sk48`, `tr87`, `tu93`, and
`wa30`, it was strongly operative on five games, safely abstained on `dc22`,
mostly abstained on `tu93`, and solved zero levels everywhere. V79 is
rejected. Positive action types are a valid substrate, but fairness over them
is not a goal model or executable procedure.

Next:

1. Keep v74 frozen as the preservation anchor. Before promotion, reproduce
   every accepted vector across the full suite.
2. Do not retry undirected rays, complement actions, or type-family fairness.
   The next offspring must compose positive effects into a falsifiable
   multi-step procedure or infer a goal-relevant state variable.
3. Cluster cross-game transition motifs around progress and irreversible
   structural events, then validate a bounded compositional hypothesis on
   synthetic or held-out structures before another public run.
4. A task promotion still requires deterministic gains on two structurally
   different games, exact preservation, the full 25-game suite, export, and
   both offline smoke paths.
5. Monitor v65b Kaggle submission `55113224` to a terminal result. Never
   attribute its eventual score to v74 or v75.

Each task mutation remains subject to the full target-repeat, preservation,
25-game, quality, and exact-export gates below. The `/goal` remains active:
`14.450686193334509 < 20`.

## Promotion gates

A descendant is accepted only if all are true:

- it adds a real level or materially improves score/efficiency;
- no accepted game completion regresses;
- the official target result is deterministic on rerun;
- the full 25-game report has exact 25/25 coverage;
- source commit and report SHA-256 are recorded;
- all tests, Ruff, and mypy pass;
- the exact candidate exports without translation;
- network-disabled Kaggle smoke passes;
- the mechanism and falsifying comparison are documented;
- `REAL_GAMES_REPORT.md` distinguishes local and Kaggle scores.

## Useful commands

```bash
.venv/bin/pytest -q
.venv/bin/ruff check reflector tests
.venv/bin/mypy reflector

.venv/bin/reflector official-run ft09 r11l tn36 lf52 \
  --environments-dir /home/pauloabelha/arc-agi-3-public-games-2026/environment_files \
  --recordings-dir /tmp/reflector-target \
  --config candidates/<candidate>.json --no-recordings --lightweight

.venv/bin/reflector official-public-run \
  --environments-dir /home/pauloabelha/arc-agi-3-public-games-2026/environment_files \
  --recordings-dir /tmp/reflector-public \
  --output reports/<result>.json \
  --config candidates/<candidate>.json --no-recordings --lightweight

.venv/bin/reflector-kaggle export \
  --config candidates/<candidate>.json --output /tmp/reflector-kaggle-dist
.venv/bin/reflector-kaggle smoke-test \
  --config candidates/<candidate>.json
```
