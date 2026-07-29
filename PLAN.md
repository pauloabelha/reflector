# Reflector persistent plan

Last updated: 2026-07-29

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
- Accepted candidate: `candidate-445450df91872736`
- Accepted agent: Reflector v37
- Accepted frozen inference commit: `c9ad1ac`
- Accepted public-development report:
  `reports/official-isolated-public-v37-enclosure-sibling-400.json`
- Accepted score: `3.9659643032130574`
- Accepted coverage: 25/25 games, 10,000 actions
- Accepted completions: 14 levels across 6 games
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

1. Record and inspect the stable `sb26` level-4 decision frame under v37;
   distinguish transition imagery before preregistering another mutation.
2. Implement `ar25` action-family causal attribution, exact-shape
   mover/target correspondence, and monotone learned translation composition;
   the rendered black-box control solved L1 in 15 actions.
3. Treat `g50t` separately as landmark/phase-conditioned topology; fixed
   endpoint orders were falsified.
4. Route qualitative frame difference and flow into causal policy only through
   typed, bounded advisors; passive perception alone is not task credit.
5. Evaluate diverse operators in isolated populations across games; require a
   new level or material efficiency gain from each operative trait.
6. Run source-matched target ablations and the full 25-game gate only for a
   qualifying offspring; keep v37 accepted otherwise.
7. Prepare the first real Kaggle notebook submission as an explicit external
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
