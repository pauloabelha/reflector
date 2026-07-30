# Reflector persistent plan

Last updated: 2026-07-29

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

- Branch: `main`
- Participant repository: `git@github.com:pauloabelha/reflector.git`
- Upstream starter remote: `https://github.com/arcprize/ARC-AGI-3-Agents.git`
- Last pushed commit: `9802d4a`
- Accepted candidate: `candidate-8c51fecdfdb99959`
- Accepted agent: Reflector v42
- Accepted frozen inference commit: `0bc1c52`
- Accepted public-development report:
  `reports/official-isolated-v42b-public-400.json`
- Accepted score: `4.442154779403533`
- Accepted coverage: 25/25 games, 10,000 actions
- Accepted completions: 17 levels across 8 games
- Kaggle public score: not submitted
- Kaggle private score: unavailable
- Canonical human-readable report: `REAL_GAMES_REPORT.md`
- Maintenance state: canonical code is organized under `reflector/core/`,
  `reflector/runtime/`, `reflector/research/`, and `reflector/evolution/`.
  Legacy top-level imports remain compatibility aliases.

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

1. Preserve accepted v42 and stop extending the `g50t` plan cap. Learn an
   explicit gate-phase experiment or switch target games; the v43c-v43f and
   integrated-Gemma runs all preserved level 1 but added no level 2.
2. Treat `m0r0` separately as equivariant multi-object composition; require
   held-out prediction of both congruent objects and obstacle-explained
   one-sided blocking before planning.
3. Route qualitative frame difference and flow into causal policy only through
   typed, bounded advisors; passive perception alone is not task credit.
4. Evaluate diverse operators in isolated populations across games; require a
   new level or material efficiency gain from each operative trait.
5. Run source-matched target ablations and the full 25-game gate only for a
   qualifying offspring; keep v42 accepted otherwise.
6. Prepare the first real Kaggle notebook submission as an explicit external
   action. Report its public score and submission status separately; private
   score remains unavailable until Kaggle exposes it.

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
