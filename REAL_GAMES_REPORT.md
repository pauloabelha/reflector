# Reflector real-games scorecard

Last updated: 2026-07-29
Canonical report: this is the only root-level report for real ARC-AGI-3 games.

## Result at a glance

> **Reflector has fully beaten 0 of 25 public-development games.**
> It has solved 19 of 183 levels across 10 games. The suite ran all 25 games,
> but evaluation coverage is not game completion.

| Outcome metric | Accepted v49b result | Meaning |
| --- | ---: | --- |
| Complete games beaten | **0 / 25** | No game was solved through its final level. |
| Games with progress | **10 / 25** | At least one level was solved in ten games. |
| Levels solved | **19 / 183** | Five in `ft09`; three each in `lp85` and `sb26`; two in `ar25`; one each in `g50t`, `lf52`, `m0r0`, `r11l`, `sp80`, and `tn36`. |
| Official local score | **4.6401724704 / 100** | About **4.64%** of the 100-point scale. |
| Evaluation coverage | **25 / 25 games** | Every public-development game was run. |
| Action budget used | **10,000** | 400 actions were allocated to each game. |
| Complete Kaggle submissions | **0** | No hidden evaluation result exists yet. |

## Evaluation surfaces

| Evaluation surface | Agent | Score | Outcome | Status |
| --- | --- | ---: | --- | --- |
| Process-isolated official local suite | v49b accepted | **4.6401724704 / 100** | 0 games beaten; 19/183 levels | 25/25 coverage |
| Process-isolated ten-game gate | v49b accepted | 11.6004311761 / 100 | 19 levels; every v47b level and action count preserved | exact twice |
| Target-only `m0r0` reruns | v49b accepted | 4.7619047619 for one game | 1/6 levels; `[20, 380]` under 400 actions | deterministic gain twice |
| Recording-enabled level-2 audit | v49b accepted | 4.7619047619 for one game | 1/6 `m0r0` levels; five repeated 12-action false-edge loops | exact accepted result reproduced; v50 diagnosis |
| Target-only symbolic offspring | v50 confirmed contextual pair transitions | 4.7619047619 for one game | 1/6 `m0r0` levels; two exact edges confirmed, third family member exposed | task and one-edge predictions falsified; rejected |
| Process-isolated official local suite | v47b accepted | **4.4496962800 / 100** | 0 games beaten; 18/183 levels | 25/25 coverage |
| Process-isolated nine-game gate | v47b accepted | 12.3602674444 / 100 | 18 levels; every v42 level preserved | exact twice |
| Target-only `sp80` reruns | v47b accepted | 0.1885375141 for one game | 1/6 levels; `[196, 204]` under 400 actions | deterministic gain twice |
| Process-isolated official local suite | v42 accepted | **4.4421547794 / 100** | 0 games beaten; 17/183 levels | 25/25 coverage |
| Process-isolated eight-game gate | v42 accepted | 13.8817336856 / 100 | 17/60 levels; every v40 action count preserved | exact twice |
| Target-only `g50t` reruns | v42 accepted | 3.5714285714 for one game | 1/7 levels; `[29, 11]` under 40 actions | deterministic gain twice |
| Process-isolated official local suite | v40 accepted | **4.2992976365 / 100** | 0 games beaten; 16/183 levels | 25/25 coverage |
| Research symbolic control, same local suite and budget | object/frame graph frontier v1 | **0.0003283918 / 100** | 0 games beaten; 1/183 levels (`vc33`) | 25/25 coverage; not a candidate |
| Target-only research hybrid | local Gemma 4 E2B + symbolic scene summary | 0.0000000000 for one game | 0/7 `g50t` levels in 40 actions | not symbolic; not Kaggle-compatible; rejected |
| Target-only integrated hybrid | v43f symbolic core + impasse-gated local Gemma 4 E2B | 3.5714285714 for one game | 1/7 `g50t` levels; `[27, 53]` in 80 actions, exactly matching symbolic v43f | not symbolic; no gain; rejected |
| Target-only symbolic offspring | v44 action-family fairness | 0.0000000000 for one game | 0/6 `sp80` levels in 400 actions | fairness operative; productive reuse absent; rejected |
| Target-only symbolic offspring | v45 primitive-grounded family reuse | 0.0000000000 for one game | 0/6 `sp80` levels in 400 actions | primitives present but behavior identical to v44; rejected |
| Source-matched historical-genome audit | v28 genome on current source | 0.0000000000 for one game | 0/6 `sp80` levels in 400 actions versus historical one level | source drift isolated to later maturity gating |
| Target-only symbolic offspring | v46 cross-retry maturity | 0.0473757834 for one game | 1/6 `sp80` levels at action 391 | real progress, but rejected: reuse began after one failure and breached preregistration |
| Target-only symbolic offspring | v46b non-bypass cross-retry maturity | 0.0673228096 for one game | 1/6 `sp80` levels at action 328, exact twice | target passed; rejected after losing `lf52` and `lp85` in preservation |
| Target-only symbolic offspring | v47 failure-conditioned fairness | 0.1885375141 for one game | 1/6 `sp80` levels at action 196, exact twice | target passed; rejected after losing `lp85` in preservation |
| Five-game transfer audit | v47b accepted | 0.0000000000 across five games | 0/34 levels in 2,000 actions | fairness and bounded reuse operative; broad transfer falsified |
| Target-only symbolic offspring | v48 boundary translation normalization | 0.0000000000 for one game | 0/6 `m0r0` levels; 147 graph states | detector correctly stayed off on growing strip; rejected |
| Target-only symbolic offspring | v48b monotone boundary normalization | 0.0000000000 for one game | 0/6 `m0r0` levels; normalization activated, 89 graph states | state normalized but coordinate-token crowding remained; rejected |
| Target-only symbolic offspring | v48c nuisance-conditioned fairness | 0.0000000000 for one game | 0/6 `m0r0` levels; 156 complex actions, 81 graph states | family balance operative; missing joint operator; rejected |
| Target-only symbolic offspring | v49 paired-object contact planning | 3.7073652991 for one game | 1/6 `m0r0` levels at action 34 | real joint-plan progress; rejected for missing ≤30 action prediction |
| Target-only symbolic offspring | v49b latent paired contact | 4.7619047619 for one game | 1/6 `m0r0` levels at action 20, exact twice | promoted after exact preservation and full-suite gates |
| Target-only symbolic offspring | v41h committed trajectory | 0.0000000000 for one game | 0/7 `g50t` levels in 400 actions | falsified; not promoted |
| Source-matched process-isolated suite | v40 exact-off / v39 policy | 4.0770754143 / 100 | 0 games beaten; 15/183 levels | exact parent reproduction |
| Process-isolated seven-game gate | v40 accepted | 15.3546344162 / 100 | 16 levels in the seven affected games | every v39 action count preserved |
| Process-isolated seven-game gate | v40 exact-off / v39 policy | 14.5609836226 / 100 | 15 levels in the seven affected games | source-matched control |
| Target-only `ar25` reruns | v40 accepted | 8.3333333333 for one game | 2/8 levels; `[17, 17, 366]` | deterministic gain twice |
| Target-only `ar25` control | v40 exact-off / v39 policy | 2.7777777778 for one game | 1/8 levels; `[17, 383]` | source-matched control |
| Process-isolated official local suite | v39 accepted | **4.0770754143 / 100** | 0 games beaten; 15/183 levels | 25/25 coverage |
| Source-matched process-isolated suite | v39 exact-off / v37 policy | 3.9659643032 / 100 | 0 games beaten; 14/183 levels | exact parent reproduction |
| Process-isolated seven-game gate | v39 accepted | 14.5609836226 / 100 | 15 levels in the seven affected games | every v37 action count preserved |
| Process-isolated seven-game gate | v39 exact-off / v37 policy | 14.1641582258 / 100 | 14 levels in the seven affected games | source-matched control |
| Target-only `ar25` reruns | v39 accepted | 2.7777777778 for one game | 1/8 levels; `[17, 383]` | deterministic gain twice |
| Target-only `ar25` control | v39 exact-off / v37 policy | 0.0000000000 for one game | 0/8 levels; `[400]` | source-matched control |
| Process-isolated official local suite | v37 accepted | **3.9659643032 / 100** | 0 games beaten; 14/183 levels | 25/25 coverage |
| Source-matched process-isolated suite | v35 control | 3.6326309699 / 100 | 0 games beaten; 13/183 levels | exact parent reproduction |
| Official local public suite | v35 historical accepted | 3.6326309699 / 100 | 0 games beaten; 13/183 levels | superseded by v37 |
| Process-isolated six-game gate | v35 accepted | 15.1359623745 / 100 | 13 levels in the six affected games | all v32 action counts preserved |
| Process-isolated six-game gate | v32 control | 14.2100364486 / 100 | 12 levels in the six affected games | source-matched control |
| Target-only `sb26` reruns | v35 accepted | 8.3333333333 for one game | 2/8 levels; `[9, 15, 376]` | deterministic structure twice |
| Process-isolated official local suite | v32 historical accepted | **3.4104087477 / 100** | 0 games beaten; 12/183 levels | superseded by v35 |
| Source-matched process-isolated suite | v32 control / v31 genome | 3.2992976365 / 100 | 0 games beaten; 11/183 levels | exact parent reproduction |
| Process-isolated official local suite | v31 historical accepted | 3.2992976365 / 100 | 0 games beaten; 11/183 levels | superseded by v32 |
| Process-isolated official local suite | v28 object/flow offspring | 2.8820272500 / 100 | 0 games beaten; 9/183 levels | rejected: lost `tn36`, slowed two wins |
| Target-only `sb26` reruns | v38 connector relocation | 16.6666666667 for one game | 3/8 levels; `[9, 15, 15, 361]` | rejected: predicted 17-action program did not advance |
| Target-only `sb26` control | v38 exact-off / v37 policy | 16.6666666667 for one game | 3/8 levels; `[9, 15, 15, 361]` | source-matched control |
| Process-isolated official local suite | v26d experimental | 2.9202784571 / 100 | 0 games beaten; 8/183 levels | replay-only efficiency gain; not promoted |
| Source-matched isolated ablation | v25 without global constraints | 2.1693300953 / 100 | 7/183 levels | controlled comparison |
| Threaded shared-process suite | v25 invalidated run | 1.9584957457 / 100 | 6/183 levels | retained as methodological negative evidence |
| Kaggle public leaderboard | v49b package ready | — | no returned score | **not submitted** |
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

### Pure symbolic graph control

To separate Reflector's constructive mechanisms from generic symbolic
exploration, a research-only graph-frontier control was run on the identical
25-game inventory with the identical 400-action-per-game budget. It proposes
simple actions and clicks on connected monochrome objects, reduces thin edge
strips, records an explicit frame-transition graph, and follows shortest known
paths to untested state-action frontiers. It contains no neural model, LLM,
game identifier, route, or training data.

The control scored **0.0003283918/100**, completed **1/183 levels** and **0/25
games**, and used all 10,000 actions. Its single `vc33` level reproduced at the
same score in a separate exact rerun. Across the suite it constructed **5,130
distinct frame states**, changed **9,185 recorded transition targets**, and
used only **203 frontier routes**. The result falsifies raw or lightly
normalized frame graphs as a sufficient 400-action solution. Animation,
autonomous dynamics, phase, and hidden commitment cause state explosion or
nonstationary edges before useful frontier return can dominate.

This does not prove that Reflector generalizes better on hidden games: v40 was
developed against the public suite, while this control was not. It does show,
on a paired local budget, that v40's object relations, learned action roles,
scheme transfer, and targeted structural solvers contribute far more than this
generic graph baseline. See the
[comparison protocol](references/SYMBOLIC_ARC3_COMPARISON.md), the
[full control report](reports/symbolic-object-graph-control-v1-400.json), and
the [exact `vc33` rerun](reports/symbolic-object-graph-control-v1-vc33-rerun-400.json).

### Runtime-LLM probe and committed-trajectory offspring

A research-only offspring was allowed to consult the locally available
`google_gemma-4-E2B-it-Q4_K_M.gguf` model through `llama.cpp`. This was Gemma
4 E2B, not Gemma 3: no Gemma 3 weight was present. The model received a
symbolic connected-component summary, frame difference, recent action/effect
history, and grounded legal action candidates. On `g50t` it produced 40/40
parseable responses with no fallback, but solved **0/7 levels**. It chose
actions `{1: 25, 2: 4, 3: 5, 4: 6}`, never chose action 5, repeated generic
exploration claims despite accumulating evidence, and made five cases where
its stated action semantics disagreed with the candidate it selected. The run
is useful negative evidence: fluent verbal hypotheses did not provide grounded
causal credit. It is not symbolic, depends on an external model process, and
is not a Kaggle-compatible candidate.

The follow-up hybrid did not replace Reflector's controller. It retained the
symbolic perception, causal ledger, schemes, topology, and planner, and opened
a Gemma arbitration gate only after at least two evidenced trajectory-gate
failures or planner disablement. The selected hybrid action was installed as
the actual symbolic `Decision` before hypothesis priming and trace recording,
so subsequent structural credit was assigned to the action really taken.

On the same 80-action `g50t` target used for v43f, this integrated hybrid
completed level 1 in 27 actions and then spent 53 actions on level 2:
**1/7 levels**, exactly the v43f symbolic result. Gemma received 27
consultations, accepted the symbolic proposal 22 times, overrode it five
times, and returned six invalid responses that safely fell back. Its typed
action grounding was still unreliable: one response hypothesized `ACTION4`
while candidate index 4 denoted and selected action 5. Continuous arbitration
also cost roughly 5.5 minutes of CPU inference for no task gain. The evidence
supports a narrower future role—one bounded typed model-mutation proposal,
followed by symbolic execution and falsification—not an LLM vote on every
action after an impasse.

The symbolic v41 branch then learned four translation effects, a four-step
committed macro, autonomous replay, and contextual collision edges from
rendered interaction alone. Successive trace-driven repairs added bounded A*
detours, pause-tolerant replay, same-level accommodation across deaths,
independent first-step planning, synchronous replay-onset recognition, and
failure-driven variation of the committed axis. These changes were operative:
the final run validated all four replay steps and accumulated 21 blocked
state-action edges. Nevertheless every recorded v41 target run completed
**0/7 `g50t` levels in 400 actions**. V41h spent 45 actions under the causal
planner, then exhausted its bounded planning or found no plan; it reset three
times and ended `GAME_OVER`.

V41 is rejected under its preregistered falsifier, which required level 1
within 30 actions twice. Its failure supplied the disequilibrium for accepted
v42, but none of v41's zero-score variants is itself promoted. The earned
insight is narrower than success: hidden phase and replay can be represented
symbolically, but a list of point collisions plus local A* is not yet a
reusable topological world model, and accommodation must preserve structural
knowledge without preserving a failed control scheme.

Raw evidence:

- [Gemma hybrid probe](reports/experimental-gemma4-hybrid-g50t-40.json)
- [Gemma + symbolic impasse arbitration](reports/experimental-gemma-symbolic-g50t-r1-80.json)
- [v41 bounded-A* run](reports/experimental-v41c-g50t-astar-r1-400.json)
- [v41 asynchronous-replay run](reports/experimental-v41d-g50t-asynchronous-replay-r1-400.json)
- [v41 cross-life accommodation run](reports/experimental-v41e-g50t-cross-life-accommodation-r1-400.json)
- [v41 independent-replay run](reports/experimental-v41f-g50t-independent-replay-r1-400.json)
- [v41 replay-onset run](reports/experimental-v41g-g50t-synchronous-replay-onset-r1-400.json)
- [v41 scheme-variation run](reports/experimental-v41h-g50t-scheme-variation-r1-400.json)

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
| v32 | 3.4104087477 | 12 | 6 | 0 | Parameterized attribute select/apply/commit composition | historical accepted |
| v35 | 3.6326309699 | 13 | 6 | 0 | Topology-guided recursive container traversal | historical accepted |
| v37 | 3.9659643032 | 14 | 6 | 0 | Enclosure-grounded sibling container composition | historical accepted |
| v39 | 4.0770754143 | 15 | 7 | 0 | Evidenced shape-goal translation with bounded occlusion | historical accepted |
| v40 | 4.2992976365 | 16 | 7 | 0 | Relational-phase-conditioned translation | historical accepted |
| v42 | 4.4421547794 | 17 | 8 | 0 | Substrate topology with uncertain-gate information actions | historical accepted |
| v47b | 4.4496962800 | 18 | 9 | 0 | Failure-conditioned fairness and cross-retry maturity | historical accepted |
| v49b | **4.6401724704** | **19** | **10** | **0** | Learned paired-object effects, contact planning, and bounded latent continuation | **current accepted** |

The equal-budget v14 control with the epistemic graph disabled scored zero.
Unconditional multicolor affordances found `tn36` but lost `r11l`; conditioning
the ontology change on observed failure preserved both. These comparisons are
why the mechanisms—not mere version succession—receive causal credit.

## Accepted v49b result

V49b inherits v47b unchanged outside one exact-off advisor. It grounds exactly
one reflected pair of congruent objects sharing a substrate, learns the ordered
pair displacement produced by plain actions, and plans in the joint anchor
state while allowing obstacles to block either component independently. If the
final planned contact action merges the two rendered components, it may repeat
only that evidenced action at most twice, stopping on progress, no effect, pair
reappearance, or the cap.

The falsification sequence matters. V48's pure-translation normalization did
not recognize a growing boundary strip. V48b recognized that nuisance but
coordinate actions still crowded exploration. V48c balanced action families
without solving the level. V49 learned the missing joint operator and reached
contact, but progress at action 34 missed its preregistered 30-action bound.
V49b represented contact as a possible intermediate latent state and completed
level 1 at action 20 in two exact target runs.

Two process-isolated ten-game gates matched exactly at
`11.600431176112412/100`: all 18 v47b levels and every inherited completed-level
action count were preserved, while `m0r0` was added at action 20. The frozen
25-game run scored `4.6401724704449645/100`, solved 19/183 levels across ten
games, used 10,000 actions, and completed 0/25 games.

Frozen inference commit:
`83287a7c2e508313fbb52b1982a921159823895e`

Candidate: `candidate-6ee87ced5a667cae`

Candidate inference fingerprint:
`f98c1e4c7fb6ee2b7f5f42f5ef051608a9e94e6879dc02662c00b55b18fddd29`

Candidate SHA-256:
`9a1ef98881ea39943162c67fcfb83cff551eef022da38c4229a9b93d5e0b841c`

Full report SHA-256:
`a21f30f0d082617d0bc042966495b208244e4e2ddae0e64c034ad67b9f84d17d`

Verification: 209 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`b2b8c81d1e1f731b2848a6739ad73685385a15fd2d5c39d7f9d8fa15e37476b2`;
the notebook SHA-256 is
`98c65734a317e3ae506abfdaaa435e5a14818755e68280e77b9e9010f13a72f1`.

### Accepted v49b progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ar25` | **2** | 8 | `[17, 17]` | 8.3333333333 | No |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `g50t` | **1** | 7 | `[27]` | 3.5714285714 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `m0r0` | **1** | 6 | `[20]` | 4.7619047619 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `sb26` | **3** | 8 | `[9, 15, 15]` | 16.6666666667 | No |
| `sp80` | **1** | 6 | `[196]` | 0.1885375141 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 15 games | **0** | 111 | `[]` | 0 | No |
| **Total** | **19** | **183** | — | **4.6401724704 overall** | **0 / 25** |

Raw evidence:

- [v49b accepted process-isolated 25-game scorecard](reports/official-isolated-v49b-public-400.json)
- [v49b exact ten-game gate 1](reports/official-isolated-v49b-ten-game-preservation-r1-400.json)
- [v49b exact ten-game gate 2](reports/official-isolated-v49b-ten-game-preservation-r2-400.json)
- [v49b exact `m0r0` rerun 1](reports/experimental-v49b-m0r0-latent-contact-r1-400.json)
- [v49b exact `m0r0` rerun 2](reports/experimental-v49b-m0r0-latent-contact-r2-400.json)
- [v49b candidate](candidates/v49b-latent-paired-contact-400.json)

The earned claim is narrow: a learned joint causal state and operator can solve
one coupled-object level that state normalization and fair exploration could
not, and rendered contact may be an intermediate state rather than completion.
This is not evidence of broad transfer, a completed game, or a Kaggle score.

## Historical accepted v47b result

V47b inherits the complete accepted v42 policy. Its one operative
accommodation separates within-episode stall from evidence accumulated across
retries of the same level. With zero failures it preserves v42's mature-stall
productive-role reuse exactly. After one failure it suppresses ambiguous
reuse. After two failures it conserves a capped maturity counter across
retries, activates bounded productive reuse, and balances finite legal action
families. Actual level progress clears the failure-conditioned state.

This distinction came from a source-matched falsification. The historical v28
genome no longer reproduced its `sp80` level on current source because a later
32-intervention maturity gate was reset on every `GAME_OVER`; each life ended
before the mechanism became reachable. V46 made maturity reachable but
violated its preregistered two-failure guard. V46b passed the target but
regressed `lf52` and `lp85`. V47 delayed fairness until two failures and
restored `lf52`, but still blocked the zero-failure parent path on `lp85`.
V47b's three-state compatibility rule was the smallest mutation that preserved
both kinds of evidence.

Two fresh target runs completed `sp80` level 1 at action 196 with allocation
`[196, 204]`. Two process-isolated nine-game gates were exact: all 17 v42
levels and their action counts were preserved, `g50t` improved from 29 to 27
actions, and `sp80` was added. The frozen-source 25-game run scored
`4.449696279968774/100`, solved 18/183 levels across nine games, used 10,000
actions, and completed 0/25 games.

Frozen inference commit:
`b9412202c3fd6a5c3f31e68d62127c00a0090fb6`

Candidate: `candidate-4c7168f7ad208c65`

Candidate inference fingerprint:
`a554f604299421357eecf6813e1d86940f6fd0b7084fbf2425ec1bfee6277879`

Candidate SHA-256:
`932d1edf8ff09b242c9c56598964fa0f579b4509d51a1b4daa925911f11ac2cf`

Full report SHA-256:
`cad20e9edb510e879a18512b2cd17a15f1fb9527355c38c890c515e494126180`

Verification: 204 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`c906d8363360f1c45862992f8fad70d6d2a1b5a62114ba2ac635ac16ba4e5abe`;
the notebook SHA-256 is
`fc5bb2adee8353cfaec112af74976ea830f4381d0e11babf74c15764f4d9f676`.

### Accepted v47b progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ar25` | **2** | 8 | `[17, 17]` | 8.3333333333 | No |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `g50t` | **1** | 7 | `[27]` | 3.5714285714 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `sb26` | **3** | 8 | `[9, 15, 15]` | 16.6666666667 | No |
| `sp80` | **1** | 6 | `[196]` | 0.1885375141 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 16 games | **0** | 117 | `[]` | 0 | No |
| **Total** | **18** | **183** | — | **4.4496962800 overall** | **0 / 25** |

Raw evidence:

- [v47b accepted process-isolated 25-game scorecard](reports/official-isolated-v47b-public-400.json)
- [v47b exact nine-game gate 1](reports/official-isolated-v47b-nine-game-preservation-r1-400.json)
- [v47b exact nine-game gate 2](reports/official-isolated-v47b-nine-game-preservation-r2-400.json)
- [v47b exact `sp80` rerun 1](reports/experimental-v47b-sp80-parent-compatible-fairness-r1-400.json)
- [v47b exact `sp80` rerun 2](reports/experimental-v47b-sp80-parent-compatible-fairness-r2-400.json)
- [v47b candidate](candidates/v47b-parent-compatible-fairness-400.json)

The earned claim is narrow but structural: for one public-development game,
preserving bounded level experience across failed episodes made an already
learned productive abstraction reachable, while conditioning exploration
fairness on repeated failure avoided interfering with fast parent solutions.
This is not evidence of hidden-game generalization or a Kaggle score.

## Historical accepted v42 result

V42 inherits the exact accepted v40 genome and activates one bounded
committed-trajectory advisor. It learns translation actions from interventions,
grounds a mover and receptacle through enclosure and hosted-marker relations,
constructs and commits a trajectory macro, and represents autonomous replay as
private causal state.

The operative change over rejected v41 is a rendered topological belief model.
After learning the movement lattice, v42 enumerates at most 128
origin-relative anchors inside the dominant connected substrate. Background
holes are structural exclusions. Non-background overlays inside that
substrate are uncertain gates rather than permanent walls. Bounded A* searches
only admitted anchors. When an evidenced gate collision disconnects every
current route, the agent performs one safe admitted information action,
advances the autonomous gate state, clears the transient collision after
actual motion, and replans.

V42a inferred 28 topology nodes and 10 uncertain gates but solved 0/7 `g50t`
levels in 40 actions because it disabled planning after the first gate
collision. That failure preregistered the v42b information-action mutation.
V42b then completed `g50t` level 1 at action 29 on two fresh 40-action runs.
In each run it used two gate-refresh actions, validated all four autonomous
replay steps, entered the newly opened substrate corridor, and reached the
rendered receptacle. The exact action allocation was `[29, 11]` twice.

Two process-isolated eight-game runs reproduced the same 17 completed levels,
every per-level action count, and every game score. All 16 inherited v40 levels
were unchanged; `g50t` level 1 was the sole addition. The full 25-game run
scored `4.442154779403533/100`, solved 17/183 levels across eight games, used
10,000 actions, and completed 0/25 games.

Frozen inference commit: `0bc1c52`

Candidate: `candidate-8c51fecdfdb99959`

Candidate inference fingerprint:
`da08f3a9828ffe16094ea5ea5e6f7d3c121f37f95cb09a532ef0c0b3eaee4043`

Candidate SHA-256:
`ed4ef6ad56c9507dd67cc7d8c420f3f62d239548ded1d4ff980c068cb0296e0d`

Full report SHA-256:
`849fd59925bbee6832de492aecef85438d83ca57b6f5802a225c4d4c2298ea05`

Verification: 191 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`7d0490d74ed0de11cb06b95b381c0b56c76ad53397566efd37815b9ee427f811`;
the notebook SHA-256 is
`e66ff2926a79f0867a52aee0b197de90d6f04be1a8e2a95e7b143775c8bdc9b7`.

### Accepted progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ar25` | **2** | 8 | `[17, 17]` | 8.3333333333 | No |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `g50t` | **1** | 7 | `[29]` | 3.5714285714 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `sb26` | **3** | 8 | `[9, 15, 15]` | 16.6666666667 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 17 games | **0** | 123 | `[]` | 0 | No |
| **Total** | **17** | **183** | — | **4.4421547794 overall** | **0 / 25** |

Raw evidence:

- [v42 accepted process-isolated 25-game scorecard](reports/official-isolated-v42b-public-400.json)
- [v42 exact eight-game gate 1](reports/official-isolated-v42b-eight-game-r1-400.json)
- [v42 exact eight-game gate 2](reports/official-isolated-v42b-eight-game-r2-400.json)
- [v42 exact `g50t` rerun 1](reports/experimental-v42b-g50t-gate-refresh-r1-40.json)
- [v42 exact `g50t` rerun 2](reports/experimental-v42b-g50t-gate-refresh-r2-40.json)
- [v42 falsified topology-only predecessor](reports/experimental-v42-g50t-substrate-topology-r1-40.json)
- [v42 candidate](candidates/v42-substrate-topology-belief-400.json)

The earned claim remains narrow. On one public-development game, a
coordinate-free substrate graph plus explicit uncertain-gate information
actions converted a learned replay macro into a successful plan. This is not
evidence of arbitrary maze solving, hidden-game generalization, or a Kaggle
score.

## Historical accepted v40 result

V40 conditions v39's learned translations on a bounded rendered phase
relation. Small rare marker components are assigned to persistent major hosts
by containment and host-relative offset. Unhosted edge animation is ignored.
When a plain intervention reassigns those markers while preserving the
mover/goal pair, the old action model is quarantined and each plain action can
be probed once under the new phase.

On `ar25` level 2, v40 first completed horizontal alignment under phase A.
One probe then transferred the rare marker pattern from the divider host to a
stationary stair host without moving the grounded pair. Under phase B, a
previously inert action acquired a stable vertical translation and was repeated
until the level advanced. Two frozen runs reproduced `[17, 17, 366]`; the
source-matched exact-off control reproduced v39 at `[17, 383]`.

The implementation itself underwent two falsifying real-game refinements.
Sources `b71ad73` and `a28e1cd` both delayed level 1 from 17 to 317 actions
because the phase layer interpreted partial occlusion as ambiguous or
untracked phase evidence. Those exact failures are retained. The final source
requires phase inference to abstain while v39's twice-confirmed bounded
occlusion continuation is active, restoring exact parent behavior.

The seven-game gate preserved every inherited completed-level action count and
added only `ar25` level 2. The full candidate reached 16/183 across seven games
at `4.29929763654639/100`; the full exact-off control reproduced v39 at
15/183 and `4.077075414324168/100`. No game was fully beaten.

Frozen inference commit: `5bb1ac6`

Candidate: `candidate-76f2aac768d8cdb0`

Candidate inference fingerprint:
`e6fb14ea7c1c729f0fc8a8264a5b7654bbba8da7a7855fe1ddda18dffa485e07`

Candidate SHA-256:
`ff150d257fa884aef5908e86ff7547b1f5cb2bc9a707b05fccadba7c4245d028`

Full report SHA-256:
`e199452dbb9791fa20b23446620256508c068d2a31f49583f93aba12f2df91ee`

Source-control report SHA-256:
`4288d3a37c0f7c7f8186ed82797825cee0b8736b27401268416c5d8e46c58aae`

Verification: 178 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`08e8c41b99eb45a52511b70e9f9b1441a96dc6edb96a61ba5c7faf3d000a5f2c`;
the notebook SHA-256 is
`3ed447340d62f398e06bfb67378c10a6294d8ee0d42177191bdc7f8589669457`.

### Accepted progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ar25` | **2** | 8 | `[17, 17]` | 8.3333333333 | No |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `sb26` | **3** | 8 | `[9, 15, 15]` | 16.6666666667 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 18 games | **0** | 130 | `[]` | 0 | No |
| **Total** | **16** | **183** | — | **4.2992976365 overall** | **0 / 25** |

Raw evidence:

- [v40 accepted process-isolated 25-game scorecard](reports/official-isolated-public-v40-relational-phase-candidate-400.json)
- [v40 full-suite exact-off control](reports/official-isolated-public-v40-relational-phase-control-400.json)
- [v40 exact `ar25` rerun 1](reports/official-isolated-v40c-ar25-r1.json)
- [v40 exact `ar25` rerun 2](reports/official-isolated-v40c-ar25-r2.json)
- [v40 exact `ar25` control](reports/official-isolated-v40c-ar25-control.json)
- [v40 seven-game preservation gate](reports/official-isolated-v40-seven-game-candidate.json)
- [v40 seven-game exact-off control](reports/official-isolated-v40-seven-game-control.json)
- [v40 first regressing target](reports/official-isolated-v40-ar25-r1.json)
- [v40 first refinement regression](reports/official-isolated-v40b-ar25-r1.json)
- [v40 candidate](candidates/v40-relational-phase-translation-400.json)
- [v40 source-matched control candidate](candidates/v40-relational-phase-control-400.json)

The earned claim is narrow: an explicitly rendered relational phase can
contextualize learned action semantics, and old semantics can be conserved
without being applied in the wrong phase. This is not evidence of arbitrary
hidden-state inference or cross-game phase transfer.

## Historical accepted v39 result

V39 adds one exact-off advisor to v37. It does not assume that resemblance
implies an affordance. It probes only plain legal actions and records a
translation when a bounded interior component preserves its attribute, area,
normalized shape, and bounding-box dimensions under a pure displacement. A
goal exists only when that mover has one stationary, differently attributed
component with the same area and normalized shape.

On `ar25` level 1, rendered transitions grounded two action translations.
The advisor then repeated only actions whose predicted displacement strictly
reduced Manhattan distance without overshooting. Two exact confirmations
licensed latent object tracking through partial overlap with the goal for at
most four steps. The frozen action trace advanced the level at action 17;
the exact-off control spent all 400 actions without advancing.

Two target runs reproduced 1/8 levels and `[17, 383]`. The seven-game gate
preserved every inherited completed-level action count and added only `ar25`
level 1. The full candidate reached 15/183 across seven games at
`4.077075414324168/100`; the source-matched exact-off control exactly
reproduced v37 at 14/183 across six games and `3.9659643032130574/100`.
No game was fully beaten.

Frozen inference commit: `c173bf8`

Evaluation source commit: `b5b57107e98d571ffea924149c2851ee604186ab`

Candidate: `candidate-e4c6c38c898dcc08`

Candidate inference fingerprint:
`acf8d79cd8c7c532b09a0cb42830d2da85766d0235224c1516eb54e80f264742`

Candidate SHA-256:
`34b3d9522085d4ed6ff09fd03eddabd768c442bc979a502fb72f2f4e674da99b`

Full report SHA-256:
`ea00d19b0c536587e4fdbcf7e7da214abbae7d7c56469dc530f6a2711c8ac1c6`

Source-control report SHA-256:
`ea8db7fb06e15934973edd874cbd8e9c24e300bda4d23b31bfa0f4ca189be20b`

Verification: 173 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`de86ec58916e3e1d6b825ce85f5c41b5ec5461d988c8c4d18533f04546eb5ebd`;
the notebook SHA-256 is
`234ad40cea8a6dfc0cdce947d0cf9bf0af186fbb49fb1ca94abe86d5bba0e859`.

### Accepted progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ar25` | **1** | 8 | `[17]` | 2.7777777778 | No |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `sb26` | **3** | 8 | `[9, 15, 15]` | 16.6666666667 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 18 games | **0** | 130 | `[]` | 0 | No |
| **Total** | **15** | **183** | — | **4.0770754143 overall** | **0 / 25** |

Raw evidence:

- [v39 accepted process-isolated 25-game scorecard](reports/official-isolated-public-v39-shape-goal-400.json)
- [v39 full-suite exact-off control](reports/official-isolated-public-v39-shape-goal-control-400.json)
- [v39 exact `ar25` rerun 1](reports/official-isolated-v39-ar25-r1.json)
- [v39 exact `ar25` rerun 2](reports/official-isolated-v39-ar25-r2.json)
- [v39 exact `ar25` control](reports/official-isolated-v39-ar25-control.json)
- [v39 seven-game preservation gate](reports/official-isolated-v39-seven-game-preservation.json)
- [v39 seven-game exact-off control](reports/official-isolated-v39-seven-game-control.json)
- [v39 candidate](candidates/v39-evidenced-shape-goal-translation-400.json)
- [v39 source-matched control candidate](candidates/v39-evidenced-shape-goal-control-400.json)

The earned claim is narrow: transition-grounded object translations can be
composed toward a uniquely matched rendered shape, and repeated exact
predictions can support bounded object permanence through partial occlusion.
This is evidence for one operative accommodation, not general object
understanding or hidden-game generalization.

## Historical accepted v37 result

V37 inherits v35's depth-first container traversal and v32's exact
reference/selector binding. V35 grouped targets by vertical coordinate, which
worked for one child on level 2 but conflated two sibling children sharing a
row on level 3. V37 grounds container identity in exact rendered rectangular
enclosures instead. Each neutral target must belong to one smallest enclosure;
missing slots become child links only through a unique appearance match.

The graph remains bounded to four containers and twelve targets and requires
one root, exact target coverage, unique child ownership, and acyclicity. On
`sb26` level 3 it emitted one root target, expanded the first two-target child,
resumed the middle root target, expanded the second child, resumed the final
root target, and committed. Two frozen runs reproduced `[9, 15, 15, 361]`.
The row-grounded v35 resolver remains an exact fallback for level 2.

The source-matched six-game v35 control reproduced 13 completed levels and
15.1359623745/100. V37 preserved every inherited completion at the same action
count and added only `sb26` level 3, reaching 14 levels and
16.5248512634/100. The process-isolated full control reproduced v35 at
`3.632630969879724/100`; v37 reached 14/183 and
`3.9659643032130574/100`. No game was fully beaten.

Frozen inference commit: `c9ad1ac164d639f1bf8993d551360709ff5d2b0d`

Candidate: `candidate-445450df91872736`

Candidate inference fingerprint:
`b698e42e378d172d6d9690c2eeb52ae48b1344996fe6cd1e76e3c35647f470f9`

Candidate SHA-256:
`ac0df61fe628482e37eb763f3aef2c4836313f7a267d530012e5fcb220e614f2`

Full report SHA-256:
`63aff02e1d4cd15296b43862e046762e7f7873b6244ad8cd0dc201422a8f586b`

Source-control report SHA-256:
`aafbbda10296e431e76d4a8e28ba773f8b224a6269f08594366e6e144442f16d`

Verification: 166 tests passed (3 skipped), Ruff passed, mypy passed, the
generic and exact-candidate network-disabled smoke paths passed, and the exact
candidate exported without translation. The overlay SHA-256 is
`2083889d12ae5072d34ea8d25de3d12b1090782273de12a5f1815fc53b9bf336`;
the notebook SHA-256 is
`dcc114e7f5f2b29efdb8b945503945b17a58b3d7119c41714c4388082ce05b92`.

### Accepted progress by game

| Game | Levels solved | Total levels | Completed-level actions | Local game score | Game beaten? |
| --- | ---: | ---: | --- | ---: | --- |
| `ft09` | **5** | 6 | `[4, 7, 14, 16, 94]` | 66.1466080321 | No |
| `lp85` | **3** | 8 | `[37, 8, 54]` | 9.7216281179 | No |
| `lf52` | **1** | 10 | `[34]` | 1.6105693614 | No |
| `r11l` | **1** | 6 | `[18]` | 4.7619047619 | No |
| `sb26` | **3** | 8 | `[9, 15, 15]` | 16.6666666667 | No |
| `tn36` | **1** | 7 | `[123]` | 0.2417306403 | No |
| Remaining 19 games | **0** | 138 | `[]` | 0 | No |
| **Total** | **14** | **183** | — | **3.9659643032 overall** | **0 / 25** |

Raw evidence:

- [v37 accepted process-isolated 25-game scorecard](reports/official-isolated-public-v37-enclosure-sibling-400.json)
- [v37 source-matched v35 control](reports/official-isolated-public-v37-v35-control-400.json)
- [v37 exact `sb26` rerun 1](reports/official-isolated-v37-sb26-r1.json)
- [v37 exact `sb26` rerun 2](reports/official-isolated-v37-sb26-r2.json)
- [v37 exact `sb26` v35 control](reports/official-isolated-v37-sb26-v35-control.json)
- [v37 six-game preservation gate](reports/official-isolated-v37-six-game-preservation.json)
- [v37 six-game v35 control](reports/official-isolated-v37-six-game-v35-control.json)
- [v37 candidate](candidates/v37-enclosure-sibling-composition-400.json)

## Rejected v38 connector-relocation hypothesis

The stable `sb26` level-4 frame contained two exact enclosures, seven neutral
targets, and one filled child-colored marker aligned with a parent target.
V38 preregistered the hypothesis that relocating the marker would construct a
parent-to-child connector while turning its old position into a neutral child
slot.

The offspring normalized the one outlined, currently selected palette object,
recovered the exact seven-color selector bijection, inferred the unique
relocation, and emitted the predicted 17 actions. The critical intervention
failed causally: selecting the marker at `(25, 36)` and applying it to
`(25, 22)` changed neither rendered location. The agent then filled the seven
predicted payload locations and committed, but the level did not advance.

Two frozen candidate runs and the current-source exact-off control all
reproduced 3/8 levels, 16.6666666667/100, and
`[9, 15, 15, 361]`. V38 is rejected without a preservation or full-suite gate.
The earned negative lesson is that geometric alignment and appearance matching
do not establish an object's action affordance; intervention must first confirm
that the proposed structural operation is executable.

Frozen inference commit: `f6b7eb579316a34a504ce6a02b19229184e297f0`

Candidate: `candidate-b3262e0992f5fae7`

Candidate inference fingerprint:
`b92f0aa94aac1f48925c1a1bff1cb18881b1712160ddb0eb5d762567168914d0`

Candidate SHA-256:
`75f8dccdb340126fa6858baf30b0c731b9672f54cbe7a3d5b1e21a0ed6d9bdce`

Frozen report SHA-256:
`c92340a5c78e9dd4f924b84fbf68409d16adb1418018dc88329485b4ca1d5f96`

Frozen rerun SHA-256:
`0de879868ceb7a59ae969e921810154b0ac59c6168f62e7c0afa59cc4abfb23d`

Source-control report SHA-256:
`43761fca742ff86a4e5880a6c32e26f64cbeab4a0807d53adade1d915cb07d04`

Raw evidence:

- [v38 frozen rejected target](reports/official-isolated-v38-connector-relocation-rejected.json)
- [v38 frozen rejected target rerun](reports/official-isolated-v38-connector-relocation-rejected-r2.json)
- [v38 source-matched exact-off control](reports/official-isolated-v38-connector-relocation-control.json)
- [v38 candidate](candidates/v38-connector-relocation-400.json)
- [v38 source-matched control candidate](candidates/v38-connector-relocation-control-400.json)

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

The real-game evidence currently supports fourteen bounded insights:

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
11. **Variation inside the wrong representation is not accommodation.** V33
   found the right target cardinality and v34 tried four flat orders, but both
   failed. V35 represented an occupied slot as a link to a child procedure,
   expanded it recursively, resumed the parent, and added a level without
   regression.
12. **Structural resemblance does not establish causal affordance.** V38
   correctly detected an aligned marker and executed its complete predicted
   program, but the proposed relocation produced no rendered change. Before
   composing a structural operation, the agent must earn its executability
   through intervention.
13. **Evidenced action semantics can support bounded object permanence.** V39
   learned translations from rendered action effects, composed only monotone
   goal-reducing instances, and used two exact predictions to carry the mover
   through a short partial occlusion. Its exact-off control solved nothing on
   `ar25`, while the enabled offspring added level 1 without regression.
14. **Action meaning can be conserved by relational phase.** V40 observed rare
   markers move between persistent hosts, quarantined the prior action model,
   and re-probed under the new relation. A formerly inert action then supplied
   the missing axis. Two regressing implementations also showed that phase
   inference must abstain when its own objects are only latently represented.

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

The historical v35 candidate also exports and passes both network-disabled smoke
paths without translation. Its generated artifact hashes are:

- overlay:
  `c466957342eb722fade306ef9e14332d9f3698c0ce1714cff1fcbf022900c95d`
- notebook:
  `c8f5d098437fdab7976680fd1ff6931406119eb9618acd117f4af9bc6678e144`

The prize audit is technically ready but still records the public repository,
participant eligibility, Kaggle rerun, and competition publication as manual
external gates. No leaderboard score exists.

The historical v37 candidate exports from the same frozen inference source and
passes both network-disabled smoke paths. Its generated artifact hashes are:

- overlay:
  `2083889d12ae5072d34ea8d25de3d12b1090782273de12a5f1815fc53b9bf336`
- notebook:
  `dcc114e7f5f2b29efdb8b945503945b17a58b3d7119c41714c4388082ce05b92`

These artifacts are technically submission-ready, but they have not been
published or scored on Kaggle.

The historical v39 candidate also exports from its frozen inference source and
passes both network-disabled smoke paths without translation. Its generated
artifact hashes are:

- overlay:
  `de86ec58916e3e1d6b825ce85f5c41b5ec5461d988c8c4d18533f04546eb5ebd`
- notebook:
  `234ad40cea8a6dfc0cdce947d0cf9bf0af186fbb49fb1ca94abe86d5bba0e859`

These historical artifacts were technically submission-ready but were not
published or scored on Kaggle.

The historical v40 candidate exports from the same frozen inference source used
for evaluation and passes both network-disabled smoke paths. Its generated
artifact hashes are:

- overlay:
  `08e8c41b99eb45a52511b70e9f9b1441a96dc6edb96a61ba5c7faf3d000a5f2c`
- notebook:
  `3ed447340d62f398e06bfb67378c10a6294d8ee0d42177191bdc7f8589669457`

These historical artifacts have not
been published or scored on Kaggle.

The historical v42 candidate exports from frozen inference source `0bc1c52`
and passes both network-disabled smoke paths without translation. Its generated
artifact hashes are:

- overlay:
  `7d0490d74ed0de11cb06b95b381c0b56c76ad53397566efd37815b9ee427f811`
- notebook:
  `e66ff2926a79f0867a52aee0b197de90d6f04be1a8e2a95e7b143775c8bdc9b7`

These historical artifacts have not been published or scored on Kaggle.

The historical v47b candidate exports from frozen inference source
`b9412202c3fd6a5c3f31e68d62127c00a0090fb6` and passes both
network-disabled smoke paths without translation. Its generated artifact
hashes are:

- overlay:
  `c906d8363360f1c45862992f8fad70d6d2a1b5a62114ba2ac635ac16ba4e5abe`
- notebook:
  `fc5bb2adee8353cfaec112af74976ea830f4381d0e11babf74c15764f4d9f676`

These historical artifacts have not
been published or scored on Kaggle.

The accepted v49b candidate exports from frozen inference source
`83287a7c2e508313fbb52b1982a921159823895e` and passes both
network-disabled smoke paths without translation. Its generated artifact
hashes are:

- overlay:
  `b2b8c81d1e1f731b2848a6739ad73685385a15fd2d5c39d7f9d8fa15e37476b2`
- notebook:
  `98c65734a317e3ae506abfdaaa435e5a14818755e68280e77b9e9010f13a72f1`

These are the current technically submission-ready artifacts. They have not
been published or scored on Kaggle.

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
