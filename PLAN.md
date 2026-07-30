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
- Accepted candidate: `candidate-6ee87ced5a667cae`
- Accepted agent: Reflector v49b
- Accepted frozen inference commit:
  `83287a7c2e508313fbb52b1982a921159823895e`
- Accepted public-development report:
  `reports/official-isolated-v49b-public-400.json`
- Accepted score: `4.6401724704449645`
- Accepted coverage: 25/25 games, 10,000 actions
- Accepted completions: 19 levels across 10 games
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
| Failure-conditioned cross-retry accommodation | v47b preserved the accepted zero-failure mature-stall path, suppressed reuse after one ambiguous failure, and conserved capped maturity plus action-family fairness only after two failures; it preserved all 17 v42 levels exactly and solved `sp80` L1 at action 196 twice. |
| Paired-object contact planning | v49b learned ordered joint effects for one reflected congruent pair, planned over independently blocked anchors, and treated planned contact as a bounded latent intermediate; it preserved all 18 v47b levels exactly and solved `m0r0` L1 at action 20 twice. |

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

1. Preserve accepted v49b. V50-v52 isolated missing goal/phase; v55 then
   showed that a correctly reached sparse marker relation is an intermediate
   transport, not a terminal goal. Accommodate the terminal classification
   while conserving its predictive transition.
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
