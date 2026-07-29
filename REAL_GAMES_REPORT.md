# Reflector real-games scorecard

Last updated: 2026-07-28  
Canonical report: this is the only root-level report for real ARC-AGI-3 games.

## Result at a glance

> **Reflector has fully beaten 0 of 25 public-development games.**
> It has solved 5 of 183 levels across 4 games. The suite ran all 25 games,
> but evaluation coverage is not game completion.

| Outcome metric | Accepted v21 result | Meaning |
| --- | ---: | --- |
| Complete games beaten | **0 / 25** | No game was solved through its final level. |
| Games with progress | **4 / 25** | At least one level was solved in four games. |
| Levels solved | **5 / 183** | Two in `ft09`; one each in `lf52`, `r11l`, and `tn36`. |
| Official local score | **0.8359967620 / 100** | About **0.836%**, not 83.6%. |
| Evaluation coverage | **25 / 25 games** | Every public-development game was run. |
| Action budget used | **10,000** | 400 actions were allocated to each game. |
| Complete Kaggle submissions | **0** | No hidden evaluation result exists yet. |

## Evaluation surfaces

| Evaluation surface | Agent | Score | Outcome | Status |
| --- | --- | ---: | --- | --- |
| Official local public-development suite | v21 accepted | **0.8359967620 / 100** | 0 games beaten; 5/183 levels | reproducible |
| Kaggle public leaderboard | v21 package ready | — | no returned score | **not submitted** |
| Kaggle private leaderboard | — | — | no returned score | unavailable |
| Target-only `ft09` run | v22 experimental | 16.7556638306 for one game | 3/6 levels | not promoted |
| Target-only `ft09` run | v23 experimental | 47.6190476190 for one game | 4/6 levels; `[4, 7, 14, 16]` actions | deterministic twice; not promoted |
| Four-game accepted-win gate | v23 experimental | 13.5583130957 across four games | 7 levels; all v21 wins preserved | passed; not a 25-game score |
| Target-only `ft09` run | v25 experimental | 66.1466080321 for one game | 5/6 levels; `[4, 7, 14, 16, 94]` actions | deterministic twice |
| Official local public-development suite | v25 rejected | **1.9584957457 / 100** | 0 games beaten; 6/183 levels | lost accepted `r11l` and `tn36` wins |

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

## Accepted v21 result

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
| v21 | **0.8359967620** | **5** | **4** | **0** | Cross-level relation transfer | **current accepted** |
| v25 | 1.9584957457 | 6 | 2 | 0 | Global overlapping relation constraints | rejected: per-game regression |

The equal-budget v14 control with the epistemic graph disabled scored zero.
Unconditional multicolor affordances found `tn36` but lost `r11l`; conditioning
the ontology change on observed failure preserved both. These comparisons are
why the mechanisms—not mere version succession—receive causal credit.

## Current experiment: v25 rejected after the full gate

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
| Strict 25-game run | 6/183 levels; `1.9584957457/100` | Five `ft09` levels and one `lf52` level; 25/25 coverage. |
| Promotion decision | rejected | Lost accepted `r11l` and `tn36` completions. |

The full run used 10,000 actions and completed `ft09` levels in
`[7, 38, 25, 21, 119]` actions and `lf52` level 1 in 36 actions. Its
environment manifest and all 25 metadata hashes exactly match v21's, so an
environment-version change does not explain the discrepancy. The target and
full-harness action counts also differ substantially. The current official
threaded harness therefore does not establish cross-context deterministic
reproducibility; game/process isolation is required before attributing all
variance to the mutation.

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

V25 passes 124 tests (3 skipped), Ruff, mypy, exact-candidate export, and both
offline package smoke paths. The accepted headline remains v21's 5/183 levels
and 0.8359967620/100 score because acceptance requires per-game
non-regression, not merely a larger aggregate.

Raw evidence:

- [v25 full 25-game scorecard](reports/official-public-evaluation-v25-global-relations-400.json)
- [v25 candidate](candidates/v25-global-relation-constraints-400.json)
- [v23 targeted evaluation summary](reports/official-targeted-evaluation-v23-summary.json)
- [v23 candidate](candidates/v23-goal-directed-relation-repair-400.json)

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

The real-game gains currently support six bounded insights:

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
6. **Construction and policy credit must remain separate.** V25's global
   constraint structure adds an `ft09` level while the full policy regresses
   on two previously solved games. A useful abstraction in one context is not
   evidence that the whole descendant should be inherited.

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
