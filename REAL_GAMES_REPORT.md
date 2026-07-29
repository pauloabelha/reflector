# Reflector real-games scorecard

Last updated: 2026-07-28  
Canonical report: this is the only root-level report for real ARC-AGI-3 games.

## Result at a glance

> **Reflector has fully beaten 0 of 25 public-development games.**
> It has solved 8 of 183 levels across 4 games. The suite ran all 25 games,
> but evaluation coverage is not game completion.

| Outcome metric | Accepted v25 result | Meaning |
| --- | ---: | --- |
| Complete games beaten | **0 / 25** | No game was solved through its final level. |
| Games with progress | **4 / 25** | At least one level was solved in four games. |
| Levels solved | **8 / 183** | Five in `ft09`; one each in `lf52`, `r11l`, and `tn36`. |
| Official local score | **2.9104325118 / 100** | About **2.91%**, not 291%. |
| Evaluation coverage | **25 / 25 games** | Every public-development game was run. |
| Action budget used | **10,000** | 400 actions were allocated to each game. |
| Complete Kaggle submissions | **0** | No hidden evaluation result exists yet. |

## Evaluation surfaces

| Evaluation surface | Agent | Score | Outcome | Status |
| --- | --- | ---: | --- | --- |
| Process-isolated official local suite | v25 accepted | **2.9104325118 / 100** | 0 games beaten; 8/183 levels | 25/25 coverage |
| Process-isolated official local suite | v26d experimental | 2.9202784571 / 100 | 0 games beaten; 8/183 levels | replay-only efficiency gain; not promoted |
| Source-matched isolated ablation | v25 without global constraints | 2.1693300953 / 100 | 7/183 levels | controlled comparison |
| Threaded shared-process suite | v25 invalidated run | 1.9584957457 / 100 | 6/183 levels | retained as methodological negative evidence |
| Kaggle public leaderboard | v25 package ready | — | no returned score | **not submitted** |
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
| v25 | **2.9104325118** | **8** | **4** | **0** | Global overlapping relation constraints | **current accepted** |
| v26d | 2.9202784571 | 8 | 4 | 0 | Successful coordinate-free role replay plus neutral construction machinery | experimental; complexity not earned |

The equal-budget v14 control with the epistemic graph disabled scored zero.
Unconditional multicolor affordances found `tn36` but lost `r11l`; conditioning
the ontology change on observed failure preserved both. These comparisons are
why the mechanisms—not mere version succession—receive causal credit.

## Accepted v25 result

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

The real-game evidence currently supports eight bounded insights:

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

The rejected v25 candidate also exports and passes the network-disabled
smoke test without translation. Its current generated artifact hashes are:

- overlay:
  `076c1232035fc4399c1064ddd4365373ea46bd76b0e29b946a63d0b8b66f3882`
- notebook:
  `2e8fdaa5c2c1e9ca2fe64715b0a2bc91ca5b010b3d5d0a6df95a14931671367e`

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
