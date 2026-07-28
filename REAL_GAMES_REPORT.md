# Reflector real-games scorecard

Last updated: 2026-07-28  
Canonical report: this is the only root-level report for real ARC-AGI-3 games.

## Current status

| Evaluation surface | Agent | Score | Levels | Coverage | Status |
| --- | --- | ---: | ---: | ---: | --- |
| Official local public-development suite | v21 accepted | **0.8359967620** | **5** | 25/25 | reproducible |
| Kaggle public leaderboard | v21 package ready | — | — | 0 submissions | **not submitted** |
| Kaggle private leaderboard | — | — | — | — | unavailable |
| Target-only development run | v22 experimental | 16.7556638306 on `ft09` | 3 | 1 game | not promoted |

The local score is not a Kaggle leaderboard score. Kaggle evaluates a separate
hidden set of 110 games: half determine the visible public score and half the
private score. Reflector has not yet crossed that evaluation boundary.

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

| Game | Level | Agent actions | Human baseline | What caused the win |
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

| Version | Public score | Levels | Main change | Decision |
| --- | ---: | ---: | --- | --- |
| v8 | 0.0000000000 | 0 | Initial symbolic research agent | baseline |
| v14 | 0.2548989649 | 2 | Epistemic state graph | promoted |
| v18 | 0.2645681905 | 3 | Failure-driven click ontology accommodation | promoted |
| v20 | 0.4550443810 | 4 | Within-frame local relation induction | promoted |
| v21 | **0.8359967620** | **5** | Cross-level relation transfer | **current accepted** |

The equal-budget v14 control with the epistemic graph disabled scored zero.
Unconditional multicolor affordances found `tn36` but lost `r11l`; conditioning
the ontology change on observed failure preserved both. These comparisons are
why the mechanisms—not mere version succession—receive causal credit.

## Current experiment: v22

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
- V22 remains experimental until it preserves all accepted wins, completes a
  strict 25-game run, and passes the exact packaged Kaggle checks.

Candidate:
[v22 conserved relation schema](candidates/v22-conserved-relation-schema-400.json)

## What our scheme is learning

The real-game gains currently support four bounded insights:

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
   the relation on overlapping panels. Level 3 suggests the structure must be
   conserved, but its constraints still need coordinated execution.

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
