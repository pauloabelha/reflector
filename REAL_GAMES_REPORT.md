# Reflector real-games scorecard

Last updated: 2026-07-29
Canonical report: this is the only root-level report for real ARC-AGI-3 games.

## Result at a glance

> **Reflector has fully beaten 0 of 25 public-development games.**
> It has solved 12 of 183 levels across 6 games. The suite ran all 25 games,
> but evaluation coverage is not game completion.

| Outcome metric | Accepted v32 result | Meaning |
| --- | ---: | --- |
| Complete games beaten | **0 / 25** | No game was solved through its final level. |
| Games with progress | **6 / 25** | At least one level was solved in six games. |
| Levels solved | **12 / 183** | Five in `ft09`; three in `lp85`; one each in `lf52`, `r11l`, `sb26`, and `tn36`. |
| Official local score | **3.4104087477 / 100** | About **3.41%**, not 341%. |
| Evaluation coverage | **25 / 25 games** | Every public-development game was run. |
| Action budget used | **10,000** | 400 actions were allocated to each game. |
| Complete Kaggle submissions | **0** | No hidden evaluation result exists yet. |

## Evaluation surfaces

| Evaluation surface | Agent | Score | Outcome | Status |
| --- | --- | ---: | --- | --- |
| Process-isolated official local suite | v32 accepted | **3.4104087477 / 100** | 0 games beaten; 12/183 levels | 25/25 coverage |
| Source-matched process-isolated suite | v32 control / v31 genome | 3.2992976365 / 100 | 0 games beaten; 11/183 levels | exact parent reproduction |
| Process-isolated official local suite | v31 historical accepted | 3.2992976365 / 100 | 0 games beaten; 11/183 levels | superseded by v32 |
| Process-isolated official local suite | v28 object/flow offspring | 2.8820272500 / 100 | 0 games beaten; 9/183 levels | rejected: lost `tn36`, slowed two wins |
| Process-isolated official local suite | v26d experimental | 2.9202784571 / 100 | 0 games beaten; 8/183 levels | replay-only efficiency gain; not promoted |
| Source-matched isolated ablation | v25 without global constraints | 2.1693300953 / 100 | 7/183 levels | controlled comparison |
| Threaded shared-process suite | v25 invalidated run | 1.9584957457 / 100 | 6/183 levels | retained as methodological negative evidence |
| Kaggle public leaderboard | v32 package ready | — | no returned score | **not submitted** |
| Kaggle private leaderboard | — | — | no returned score | unavailable |
| Target-only `ft09` run | v22 experimental | 16.7556638306 for one game | 3/6 levels | not promoted |
| Target-only `ft09` run | v23 experimental | 47.6190476190 for one game | 4/6 levels; `[4, 7, 14, 16]` actions | deterministic twice; not promoted |
| Four-game accepted-win gate | v23 experimental | 13.5583130957 across four games | 7 levels; all v21 wins preserved | passed; not a 25-game score |
| Target-only `ft09` run | v25 experimental | 66.1466080321 for one game | 5/6 levels; `[4, 7, 14, 16, 94]` actions | deterministic twice |
| Four-game process-isolated gate | v25 accepted | 18.1902031989 across four games | 8 levels; all prior wins preserved | exact twice |
| Four-game process-isolated gate | v26d experimental | 18.2517403567 across four games | 8 levels; all prior wins preserved | exact twice |
| Target-only `ft09` run | v26e experimental | 66.3927566633 for one game | 5/6 levels; 2 composite trials | deterministic twice; no task gain |
| Target-only `ft09` run | v26f experimental | 66.3927566633 for one game | 5/6 levels; replay fell from 55 to 12 actions | deterministic twice; no task gain |

These surfaces must not be combined. The accepted local result uses 25 known
public-development games. Kaggle evaluates a separate hidden set of 110 games:
half determine the visible public score and half the private score. Reflector
has not yet crossed that evaluation boundary.

### Reporting terms

- **Game beaten:** the agent completed every level in that game.
- **Game with progress:** the agent completed at least one level, but possibly
  not the whole game.
- **Level solved:** the environment reported advancement to the next level.
- **Evaluation coverage:** the game was run and returned a result. It says
  nothing about whether the agent solved it.
- **Local score:** Relative Human Action Efficiency averaged over the 25 local
  games, on the official 0–100 scale. Unsolved games contribute zero.
- **Kaggle score:** a score returned by an actual hidden Kaggle evaluation.
  Export and smoke-test success do not create a Kaggle score.

Official competition links:

- [Kaggle competition and scoring](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data)
- [Kaggle public leaderboard](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/leaderboard)
- [ARC Prize competition requirements](https://arcprize.org/competitions/2026/arc-agi-3)

## Historical v21 result

Frozen inference commit: `e7037b4a5a2ac56b026f9ca3acbd559bbd0cb0fc`  
Candidate: `candidate-3332b36c8afa95aa`  
Actions: 10,000  
Report SHA-256:
`59e09da642949de4897917ca6cea1fb7a00771d7adbbb445283dc6f09fa61417`

### Progress by game

| Game | Levels solved | Total levels | Complete game beaten? | Local game score |
| --- | ---: | ---: | --- | ---: |
| `ft09` | **2** | 6 | No | 14.2857142857 |
| `lf52` | **1** | 10 | No | 1.6105693614 |
| `r11l` | **1** | 6 | No | 4.7619047619 |
| `tn36` | **1** | 7 | No | 0.2417306403 |
| Remaining 21 games | **0** | 154 | No | 0 |
| **Total** | **5** | **183** | **0 / 25 beaten** | **0.8359967620 overall** |

No level was solved in: `ar25`, `bp35`, `cd82`, `cn04`, `dc22`, `g50t`,
`ka59`, `lp85`, `ls20`, `m0r0`, `re86`, `s5i5`, `sb26`, `sc25`, `sk48`,
`sp80`, `su15`, `tr87`, `tu93`, `vc33`, and `wa30`.

### Solved-level efficiency

| Game | Level | Agent actions | Human baseline | What caused the level completion |
| --- | ---: | ---: | ---: | --- |
| `ft09` | 1 | **4** | 43 | Induced local same/different constraints from three rendered examples. |
| `ft09` | 2 | **7** | 12 | Retained the induced relation and transferred it to overlapping panels with no solved example. |
| `r11l` | 1 | **18** | 22 | Epistemic state-graph exploration preserved distinct intervention outcomes. |
| `lf52` | 1 | **34** | 32 | Epistemic state-graph exploration found the successful click sequence. |
| `tn36` | 1 | **123** | 32 | After failure contradicted the original object ontology, multicolor affordance accommodation exposed the actionable region. |

Raw evidence:

- [v21 full 25-game scorecard](reports/official-public-evaluation-v21-cross-level-relations-400.json)
- [v21 targeted promotion gate](reports/official-targeted-evaluation-v21-summary.json)
- [v21 candidate](candidates/v21-cross-level-relation-transfer-400.json)

## Score evolution

| Version | Local score / 100 | Levels solved | Games with progress | Games beaten | Main change | Decision |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| v8 | 0.0000000000 | 0 | 0 | 0 | Initial symbolic research agent | baseline |
| v14 | 0.2548989649 | 2 | 2 | 0 | Epistemic state graph | promoted |
| v18 | 0.2645681905 | 3 | 3 | 0 | Failure-driven click ontology accommodation | promoted |
| v20 | 0.4550443810 | 4 | 4 | 0 | Within-frame local relation induction | promoted |
| v21 | 0.8359967620 | 5 | 4 | 0 | Cross-level relation transfer | historical threaded result |
| v25 ablation | 2.1693300953 | 7 | 4 | 0 | Current source, global constraint solver disabled | process-isolated control |
| v25 | 2.9104325118 | 8 | 4 | 0 | Global overlapping relation constraints | accepted parent |
| v26d | 2.9202784571 | 8 | 4 | 0 | Successful coordinate-free role replay plus neutral construction machinery | experimental; complexity not earned |
| v28 | 2.8820272500 | 9 | 5 | 0 | Visual/temporal object primitives plus bounded role reuse | rejected: one accepted level regressed |
| v29 | 2.9338884001 | 9 | 5 | 0 | Mature-stall bounded causal role reuse | historical accepted |
| v30 | 3.1894439557 | 10 | 5 | 0 | Learned marker-relative goals plus composed cyclic transports | historical accepted |
| v31 | 3.2992976365 | 11 | 5 | 0 | Grounded non-axis-aligned graph-cycle transport | historical accepted |
| v32 | **3.4104087477** | **12** | **6** | **0** | Parameterized attribute select/apply/commit composition | **current accepted** |

The equal-budget v14 control with the epistemic graph disabled scored zero.
Unconditional multicolor affordances found `tn36` but lost `r11l`; conditioning
the ontology change on observed failure preserved both. These comparisons are
why the mechanisms—not mere version succession—receive causal credit.

## Accepted v32 result

V32 adds one exact-off mechanism to v31. It searches a rendered frame for
three structurally corresponding rows: an ordered reference row whose objects
carry distinct attributes, an unordered selector row with the exact same
attribute set, and an intervening row of identical neutral targets. When this
strong visual isomorphism exists, the agent binds each reference attribute to
its matching selector and corresponding target slot.

On `sb26` level 1, the inferred program was four
`select(attribute) -> apply(slot)` pairs followed by the first unused
non-click control as a commit hypothesis. It advanced in nine actions. The
advisor then stayed silent on level 2 because the same structure was absent;
the remaining 391 actions produced no further progress. Two independent
target runs reproduced `[9, 391]`.

The current-source exact-off target control exhausted 400 actions at 0/8. The
six-game gate preserved all eleven v31 completions at their exact action
counts and added `sb26`. The full exact-off control reproduced v31 at 11/183
and `3.2992976365463904/100`; v32 reached 12/183 across six games and
`3.4104087476575016/100`. No game was fully beaten.

Frozen inference commit: `bdcede098f7e565e5e1adab64ac3bf48bc4dc81a`

Candidate: `candidate-e9c00d0968c2832a`

Candidate inference fingerprint:
`68977761ee8fdaa2b280f078ed7fcde321680cf0fbc3c526a7347175639c4469`

Candidate SHA-256:
`ec6317dd0a7a2652bb5ecef7bd78236ec07d9017036db2ed8f4b8fb34e41a389`

Full report SHA-256:
`c31163447b98d4628ea0d57eef371d2d8ade0712578ffcc524820d255af70005`

Source-control report SHA-256:
`1cb2d5e671082c6aabe5a8dc02545151d6c945195ce26c99e64314eb28fa074e`

Verification: 158 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`ad330f1dfc7686210a16696d1de584e5b6d7bc27470ca0624e1d49ed89f35181`;
the notebook SHA-256 is
`9428745f9dce0bf5cc44217a21f0c2b4e183289d6459d7aff914cf3ed3b5c904`.

### Accepted progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `sb26` | **1** | 8 | `[9]` | 2.7777777778 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 19 games | **0** | 138 | `[]` | 0 | No |
| **Total** | **12** | **183** | — | **3.4104087477 overall** | **0 / 25** |

Raw evidence:

- [v32 accepted 25-game scorecard](reports/official-isolated-public-v32-parameterized-select-apply-commit-400.json)
- [v32 source-matched v31 control](reports/official-isolated-public-v32-source-control-400.json)
- [v32 exact `sb26` rerun](reports/official-isolated-v32-sb26-r2.json)
- [v32 exact-off `sb26` control](reports/official-isolated-v32-sb26-source-control.json)
- [v32 six-game preservation gate](reports/official-isolated-v32-six-game-gate.json)
- [v32 candidate](candidates/v32-parameterized-select-apply-commit-400.json)

## Historical accepted v31 result

V31 adds one exact-off mechanism to v30. When the rectangular transport
language does not explain a marked scene, it enumerates a bounded set of
chordless token cycles. A controller is bound to a cycle only after the
rendered transition is an exact conserved one-step rotation. The agent retains
that episode-local permutation, identifies shared slots between cycles, and
composes only evidenced transports toward the already learned marker-match
goal.

On `lp85` level 3, the two target marker appearances begin on opposite
16-token cycles and must pass through two shared junctions. V30 never invoked
its rectangular advisor and exhausted 355 actions. V31 spent 34 actions
discovering two causal controller permutations, then executed a 20-action
bounded plan and advanced. Independent runs reproduced level actions
`[37, 8, 54, 301]`.

The first six-worker full-suite attempt was terminated without a scorecard
because the graph frontier was not operationally bounded. That descendant was
not accepted. The corrected inference path caps token nodes at 64, graph
degree at four, DFS expansions/frontier at 8,192, and cyclic interventions at
24. It reproduced the target, completed the full 25-game suite with three
isolated workers, and preserved every v30 action count.

The exact-off full control reproduced v30 at 10/183 and
`3.1894439557050553/100`. V31 reached 11/183 and
`3.2992976365463904/100`. No game was fully beaten.

Frozen inference commit: `cde92a9da104c3bb2d3662b6f50de268cae3d51f`

Candidate: `candidate-98a22d6f908c6eb7`

Candidate inference fingerprint:
`4b9a3640759805debe7bbfec4f664ea4ae5df60d5f3905cba6ab8f4f93a601bf`

Candidate SHA-256:
`8ba6a13412dcf91693c2b56b49bc14df6e882cc638b3ce9e72acc3a1880b604a`

Full report SHA-256:
`16420b1f870353fe4287c0d4e3df0d2e13a5aa6402a3a6680d05517ca2c3f2ea`

Source-control report SHA-256:
`7977d4e1e87ae47bac507983a594332fe702172f2794ac85184ed6032afc9531`

Verification: 155 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`9aa5bb707e769eaefebbfa085132a7544c424c58fe1b9a98df8014d5492ac266`;
the notebook SHA-256 is
`75f82cdfa847e725acdf69f81c6c77590f9b0502b8d00c1574562f0ae8e8b464`.

### Accepted progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 20 games | **0** | 146 | `[]` | 0 | No |
| **Total** | **11** | **183** | — | **3.2992976365 overall** | **0 / 25** |

Raw evidence:

- [v31 accepted 25-game scorecard](reports/official-isolated-public-v31-grounded-graph-cycle-transport-400.json)
- [v31 source-matched v30 control](reports/official-isolated-public-v31-source-control-400.json)
- [v31 bounded exact `lp85` rerun](reports/official-isolated-v31-bounded-lp85-r3.json)
- [v31 five-game preservation gate](reports/official-isolated-v31-five-game-r2.json)
- [v31 candidate](candidates/v31-grounded-graph-cycle-transport-400.json)

## Historical accepted v30 result

V30 adds one exact-off mechanism to v29. It detects a token structurally marked
by four smaller, identical corner components. Responsive interventions are
credited as cyclic transports only when they conserve the ordered token
multiset and produce an exact one-step rotation. A marker-match goal is learned
only when an already evidenced transport predicts the transition that advances
the level; the winning transition is construction evidence and is not
retroactively credited to the newly constructed scheme.

On the next level, the learned scheme is rebound to translated, resized, and
recolored structures. The agent factors one outer perimeter and two horizontal
tracks whose positions overlap, associates mirrored controllers by relative
position, and searches their composed effects. Search is capped at 8,192
expansions and the advisor at 24 interventions per level.

The `lp85` trace supplied the causal falsifier. V29 solved level 1 in 37 actions
but spent the remaining 363 interventions on level 2. V30 preserved the same
37-action first level, constructed the marker-match relation from progress,
and solved level 2 in exactly eight cyclic-advisor actions. Two independent
isolated runs reproduced `[37, 8, 355]`. The five-game gate preserved every
v29 action count. The source-matched full control reproduced v29 exactly at
9/183 and `2.9338884001495003/100`; v30 reached 10/183 and
`3.1894439557050553/100`. No game was fully beaten.

### Accepted progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `lp85` | **2** | 8 | `[37, 8]` | 6.9752860969 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 20 games | **0** | 146 | `[]` | 0 | No |
| **Total** | **10** | **183** | — | **3.1894439557 overall** | **0 / 25** |

The trailing action counts in each raw run are budget spent on the next
unsolved level: `ft09` 265, `lp85` 355, `lf52` 366, `r11l` 382, and `tn36`
277. They are not additional solved-level costs.

Frozen inference commit: `e2ba274042ca453d359dc86964b5b55374940a2d`

Candidate: `candidate-2fabaa20cd4cd160`

Candidate inference fingerprint:
`bf5a5b1fdbac7bd6f7c971d1e2c271aa6b8f2a0d5840c0acdd2af3680d00e69f`

Candidate SHA-256:
`2911747c27a6fd1ee1f29755525a454c2cf9b018e7b6777c84aa80ecf9aa9f94`

Full report SHA-256:
`70f2ad4689f4e0b2883f42a4cea8da0c4687c3fb7407931ea3b154a17e617d6c`

Source-control report SHA-256:
`bbd6a01b4efed6768a68571f956c08170af11a8f127e3de0869599451daa2421`

Verification: 153 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`ccea9c9ebbf2f0687e120c02d1cf64751e9bf2287afabbb16525acd7a107cb8a`;
the notebook SHA-256 is
`8a630a11c34b8d0d1e77a100057ad5e711a38bbe2693797a58639a160d34d92b`.

Raw evidence:

- [v30 accepted 25-game scorecard](reports/official-isolated-public-v30-marker-relative-cyclic-transport-400.json)
- [v30 source-matched v29 control](reports/official-isolated-public-v30-source-control-400.json)
- [v30 five-game preservation gate](reports/official-isolated-v30-five-game-r2.json)
- [v30 exact `lp85` rerun](reports/official-isolated-v30-lp85-r3.json)
- [v30 candidate](candidates/v30-marker-relative-cyclic-transport-400.json)

## Historical accepted v29 result

V29 adds one bounded policy to the accepted v25 parent. After 32 interventions
without level progress, the explorer may reuse an action role only if that role
has already caused a rendered response. Reuse is capped at eight trials per
level. A conserved learned relation suppresses this advisor, so causal reuse
cannot displace the relation-repair mechanism that already solves `ft09`.

The mutation came from watching five rendered games and inspecting their
cognitive streams. The unbounded donor found `lp85` level 1 but regressed
`ft09`; priority repair restored four `ft09` levels but still stalled; bounding
reuse restored five. A six-game ablation then separated the traits:

- primitive intervention alone improved `ft09` but lost `r11l` and `tn36`;
- action-family fairness lost `lf52`;
- causal reuse without primitive actions added `lp85` while preserving every
  accepted level, but initially slowed `ft09` and `r11l`;
- delaying reuse to mature stagnation restored the exact accepted action counts
  and retained `lp85` in 37 actions, twice.

The final source-matched 25-game gate reproduced v25 at
`2.9104325118287466/100` and 8 levels. V29 scored
`2.9338884001495003/100`, solved 9 levels across 5 games, and preserved
`ft09`, `lf52`, `r11l`, and `tn36` at their exact parent action counts. It
added only `lp85` level 1. No game was fully beaten.

Frozen inference commit: `54db179`

Candidate: `candidate-309548c858c10616`

Candidate inference fingerprint:
`2648e2005e0954ed9a31dbb181df49c442388821f7be06fea1ba8fc2db77f1d5`

Full report SHA-256:
`f2d7f21e634d72a77bc0044cd5456e6645cf7889228824017b4d028bc467b51d`

Verification: 148 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation.

Raw evidence:

- [v29 accepted 25-game scorecard](reports/official-isolated-public-v29-mature-causal-role-reuse-400.json)
- [v29 source-matched control](reports/official-isolated-public-v29-source-control-400.json)
- [v29 exact six-game run 1](reports/official-isolated-v29-six-game-r1.json)
- [v29 exact six-game run 2](reports/official-isolated-v29-six-game-r2.json)
- [v29 candidate](candidates/v29-mature-causal-role-reuse-400.json)
- [rejected v28 full scorecard](reports/official-isolated-public-v28-bounded-causal-object-primitives-400.json)

## Parent v25 result

V25 coordinates overlapping clue constraints on one inferred tile lattice. It
does not use game IDs, fixed coordinates, or fixed colors. Each deployed action
also flushes a bounded cognitive event containing advisor arbitration,
transition evidence, and construction deltas; the deployed agent never calls
an LLM.

### Evidence and decision

| Surface | Result | Interpretation |
| --- | --- | --- |
| `ft09` target runs 1–2 | 5/6; `[4, 7, 14, 16, 94]` both times | Added level 5 by coordinating overlapping constraints. |
| Four-game gate | 8 levels | Preserved the five accepted v21 completions and added three. |
| Source-matched isolated ablation | 7/183; `2.1693300953/100` | Same source and genome except global constraint solver disabled. |
| Process-isolated strict 25-game run | 8/183; `2.9104325118/100` | Preserved all control completions and added `ft09` level 5. |
| Promotion decision | accepted | Positive one-factor result with 25/25 coverage and no per-game regression. |

The accepted run used 10,000 actions. It completed `ft09` levels in
`[4, 7, 14, 16, 94]`, `lf52` level 1 in 34, `r11l` level 1 in 18, and `tn36`
level 1 in 123. The source-matched ablation completed the first four `ft09`
levels in `[4, 7, 14, 16]` and reproduced the other three games exactly.

The earlier shared-process threaded run produced different results because the
official `Swarm` interleaved all game environments in threads. It is retained
for audit but no longer used for promotion. The corrected evaluator runs each
game in a fresh Python process while retaining bounded parallel execution.

The bounded positive result is real: one symbolic relation progressed from
isolated panels to overlapping constraints and solved another level. It is
still within one game family and did not preserve broader competence.

### What the cognitive stream exposed

All 10,000 actions produced a structured JSONL event. Advisor selection was:

| Selected advisor | Actions |
| --- | ---: |
| Untried state intervention | 9,781 |
| Global/local relation repair | 126 |
| Known state-graph navigation | 4 |
| Reset handled outside arbitration | 89 |

At least 3,013 construction assessments confirmed a predicted no-effect. This
is not necessarily predictive failure: the model can correctly expect that an
action changes nothing. It is pragmatic failure when the policy continues to
spend its finite budget without progress. The next design must therefore keep
three credits typed and separate:

1. external task progress and delayed action credit;
2. prediction confirmation or contradiction;
3. construction credit for a representation that improves future control.

This is the concrete RL/genetic-epistemology junction. Prediction error can
trigger accommodation, while sustained zero-progress return must create a
separate pragmatic disequilibrium signal. One scalar reward or one generic
“surprise” signal would erase the distinction revealed by these traces.

V25 passes 126 tests (3 skipped), Ruff, mypy, exact-candidate export, and both
offline package smoke paths.

Raw evidence:

- [v25 accepted process-isolated scorecard](reports/official-isolated-public-evaluation-v25-global-relations-400.json)
- [v25 process-isolated ablation](reports/official-isolated-public-evaluation-v25-global-relations-ablation-400.json)
- [invalidated threaded v25 scorecard](reports/official-public-evaluation-v25-global-relations-400.json)
- [v25 candidate](candidates/v25-global-relation-constraints-400.json)
- [v23 targeted evaluation summary](reports/official-targeted-evaluation-v23-summary.json)
- [v23 candidate](candidates/v23-goal-directed-relation-repair-400.json)

## Experimental v26: constructive credit and scheme composition

V26 implements the requested bridge between reinforcement learning and genetic
epistemology without calling an LLM during play:

- every intervention preregisters a causal hypothesis before its outcome;
- predictive support/refutation is kept separate from pragmatic
  progress/stagnation;
- credit names the exact licensing structures and any composite scheme;
- successful action-role programs become first-class schemes that can be
  supplied to other schemes by prefix, suffix, interleaving, or role binding;
- sustained pragmatic stagnation, rather than mere prediction error, opens
  bounded variation;
- a failed composite application is falsified while its base, argument, and
  operator remain eligible for a different binding.

This capacity is operative, not merely serialized: the combined v26 offspring
preregistered 400 hypotheses, constructed 37 parameterized schemes, and tried
12 of them on `ft09`. The score evidence is more limited. Credit alone and
scheme variation alone were exact ties. Successful coordinate-free role replay
was the only population trait to pass the target inheritance gate. Bred v26d
preserved all eight accepted level completions and increased the isolated
25-game score from 2.9104325118 to 2.9202784571 by changing `ft09` efficiency,
but it added no level and the new constructive machinery did not cause that
gain. V25 therefore remains accepted: inheriting neutral complexity would
violate the project’s own credit-assignment rule.

Trace inspection then falsified two refinements:

- v26e reduced repeated parameterized applications from 12 to 2, with no score
  or level change;
- v26f suspended a stale successful replay after pragmatic disequilibrium,
  reducing replay from 55 to 12 actions, but the released budget became
  undirected novelty and again changed neither score nor levels.

These are useful negative results. They show that correctly retiring a scheme
is not enough; the missing mechanism is a constructive relational binder that
maps a modifier’s role variables into another scheme’s objects and control
parameters, then grounds that binding into an intervention.

Raw evidence:

- [v26 population and targeted summary](reports/official-targeted-evaluation-v26-summary.json)
- [v26d full-suite experimental result](reports/official-isolated-public-evaluation-v26d-constructive-replay-400.json)
- [v26 source-matched full-suite control](reports/official-isolated-public-evaluation-v26-source-control-400.json)
- [v26e–v26f targeted falsification summary](reports/official-targeted-evaluation-v26ef-summary.json)
- [v26f candidate](candidates/v26f-disequilibrium-arbitration-400.json)

### V22–v23 parent results

V21 failed `ft09` level 3 because it overwrote a proven relation when it saw
four new unsolved panels. V22 conserves the induced relation until outcome
contradiction justifies accommodation.

Target result:

| Game | Level actions | Outcome |
| --- | --- | --- |
| `ft09` | `[4, 7, 152]` | Added level 3, but inefficient versus the 23-action human baseline. |

Interpretation:

- The new level supports schema conservation across novel content.
- The 152-action result is not yet good control.
- Eleven initial relation-guided interventions were followed by a long flat
  fallback before the last required macro-cell corrections were rediscovered.
- V22 supplied the conserved schema used by v23, but v23 supersedes it as the
  active experiment because the goal-directed arbitration reduces level 3
  from 152 to 14 actions and adds level 4.

Candidate:
[v22 conserved relation schema](candidates/v22-conserved-relation-schema-400.json)

## What our scheme is learning

The real-game evidence currently supports ten bounded insights:

1. **Exploration needs memory of intervention identity.** Treating every frame
   independently scored zero; an epistemic transition graph produced the first
   two levels.
2. **Accommodation should follow contradiction.** Changing ontology
   unconditionally destroyed a prior success. Changing it after `GAME_OVER`
   retained old competence and added a new game.
3. **Relations can control action directly.** `ft09` level 1 was solved by
   inducing a symbolic relation from rendered examples, without game IDs,
   fixed coordinates, or fixed colors.
4. **Operative structure can transfer across changed layouts.** Level 2 reused
   the relation on overlapping panels, and v22 showed that the structure must
   remain conserved rather than be overwritten by unsolved examples.
5. **Active constraints should guide exploration.** On `ft09`, moving
   relation-implied repairs ahead of undirected novelty reduced level 3 from
   152 to 14 actions and added level 4 in 16 actions. This is within-game
   evidence only.
6. **Construction and policy credit must remain separate.** V26 constructs and
   executes parameterized schemes, but only coordinate-free replay changed the
   official score. Operative structure is not automatically useful structure.
7. **Prediction and task return are different signals.** A no-effect
   prediction can be correct while the intervention is pragmatically useless.
   Scalarizing both would reward stagnation.
8. **Accommodation needs a successor, not only inhibition.** V26f correctly
   suspended a stale replay, but undirected novelty consumed the recovered
   budget. Falsification creates room for learning; it does not itself create
   the next relational scheme.
9. **Responsive roles need mature-stall gating.** Immediate or unbounded reuse
   slowed accepted wins. Waiting 32 interventions, capping reuse at eight, and
   conserving an active relation retained all parent action counts and added
   `lp85`.
10. **A richer ontology is not automatically a better policy.** V28's
   composite, enclosure, shape, frame-difference, and flow primitives were
   typed and operative, but active use lost `tn36` and slowed two games.
   Perceptual structure must earn control credit independently.

These are narrow environment-level results. They do not yet prove general
Piagetian equilibration, arbitrary schema induction, cross-game transfer, or
competitive hidden performance.

## Kaggle readiness

The exact v21 candidate:

- exports as the official starter-compatible notebook and inference overlay;
- runs with no LLM, internet, database, or server;
- passes the network-disabled packaged smoke test;
- initializes, receives an observation, emits a legal action, advances the
  official fixture environment, and terminates cleanly.

Artifact hashes:

- overlay:
  `0b9580fefba5f87efea6df351877d83d01f3704d591b7d79574c420c3f2c0033`
- notebook:
  `28b86409357fb15270d7a9b5a40257609b91e899892b6728861fc8b82902ddc7`

Package readiness is not evaluation. The next external milestone is an
explicit Kaggle notebook submission and its returned public score.

The accepted v29 candidate exports and passes the network-disabled smoke test
without translation. Its generated artifact hashes are:

- overlay:
  `29bc5577a692941e0ae22e946427b009a18db4c62250eb39581d5832e387e0d7`
- notebook:
  `3a30064d4504ab61db83b18f1e315657d42d7c2a8f982a278f50a622287c1600`

These hashes prove package identity and compatibility, not promotion or score.

## Reporting protocol

This file is updated whenever:

- an accepted real-game level or score changes;
- a descendant is rejected for regression;
- a full 25-game evaluation finishes;
- a Kaggle submission starts, fails, or receives a score;
- public/private leaderboard status changes;
- evidence changes which symbolic mechanism deserves causal credit.

Raw scorecards remain immutable under `reports/`. The live continuation state
and next experiment are maintained in [PLAN.md](PLAN.md).

Every future headline must state all of the following separately:

1. complete games beaten out of games evaluated;
2. games with at least one solved level;
3. levels solved out of total levels;
4. local score explicitly written as “out of 100”;
5. evaluation coverage;
6. Kaggle submission count and returned public/private scores.

Never use “complete” as shorthand for coverage. Use “evaluated” for coverage
and reserve “beaten” or “fully completed” for finishing every level of a game.
