# ARC-AGI-3 public-game evaluation

Evaluation date: 2026-07-28

Primary evidence:

- [v14 epistemic-graph result](reports/official-public-evaluation-v14-graph-400.json)
- [v14 exact equal-budget control](reports/official-public-evaluation-v14-control-400.json)
- [v15 targeted rejected-descendant summary](reports/official-targeted-evaluation-v15-summary.json)
- [v16 targeted neutral-descendant summary](reports/official-targeted-evaluation-v16-summary.json)
- [complete official-harness result](reports/official-public-evaluation-v8.json)
- [compact result summary](reports/official-public-evaluation-v8-summary.json)
- [historical access preflight](reports/public-game-evaluation-2026-07-28.json)

## Verdict

**The current accepted Reflector v14 agent scores 0.2548989649 on the 25
official public ARC-AGI-3 games. It completes two levels across two games.
This is a causal improvement over both v8 and an exact equal-budget v14
control, but it is still far from competitive performance.**

This is the first legitimate environment-level test of the research platform.
It proves that the agent is runnable, submission-compatible, and capable of
limited public-game progress. It still contradicts any claim that the current
symbolic mechanisms are competitive.

| Result | Reflector v14 graph | v14 control | Reflector v8 | Random starter |
| --- | ---: | ---: | ---: | ---: |
| Public games reported | 25/25 | 25/25 | 25/25 | 25/25 |
| ARC score | 0.2548989649 | 0.0 | 0.0 | 0.0 |
| Levels completed | 2 | 0 | 0 | 0 |
| Actions | 10,000 | 10,000 | 2,025 | 2,025 |

The v14 graph completed level 1 of `r11l` in 18 actions and level 1 of
`lf52` in 34 actions. The exact control changed only
`enable_epistemic_state_graph` to false while retaining the 400-action budget;
it completed no levels. The public-suite result SHA-256 values are:

- graph: `39c5a7ed678650be9dd0b4638e889a9fdcde6c6a9da3a0a25e08fb2f16602d75`
- control: `3a509ddb474f711920330d55aae24aa7db08aa904f30e9e2334e4d481f28598d`

The random result is one stochastic reference run, not a confidence interval.
The paired deterministic control is the stronger causal comparison.

## Subsequent descendants

Two isolated mechanisms were tested after v14:

1. v15 hierarchical action-family fairness balanced mixed action spaces, but
   regressed `lf52` from one level to zero. It was rejected.
2. v16 compiled successful trajectories into coordinate-free action-role
   programs. It preserved both v14 wins but advanced no additional level, so it
   was retained as a neutral ablation and not promoted.

These negative results are intentionally retained. The evidence indicates that
flat coordinate novelty is weak, but equal action-family allocation is too
aggressive and coarse roles `(action, color, area, shape)` omit the relational
structure required for transfer.

## Provenance and execution

The games were enumerated and downloaded through the official ARC-AGI Toolkit's
documented anonymous-key flow. It returned exactly 25 current versioned public
games. The Kaggle archive itself remained account-gated, so byte identity with
that archive was not independently checked.

- Frozen source commit:
  `1cd73e24e99e92de870243277f4938da3a2162f1`
- Agent version: `reflector-symbolic-v13`
- Unique game IDs: 25
- Metadata inventory SHA-256:
  `d3ea8336b4534e4a8f5a5789fa910ad0cc9be2e40943e0803f9ec5ef88b9b25a`
- Complete 50-file environment manifest SHA-256:
  `8b7b1bf84e68bd0453d3970cabdac2f8c8cba06c0598b70bb3e32ff0128ff9d9`
- Structured result SHA-256:
  `cca07a3f571697ceea4b93d1cb308a5f1700bee47de83a769f537bc45a52f3d9`
- Coverage: 25 discovered, 25 reported, complete
- Operation mode: official `Swarm`, local/offline

The test ran from a detached worktree, so unrelated uncommitted
concept-lifecycle work in the main checkout did not enter the evaluated agent.

The official Swarm opened at 14:41:09 and closed at 14:41:48 local time,
approximately 39 seconds of concurrent play. Trace evaluation and report
serialization then took approximately 27 seconds. Per-agent `seconds` values
in the raw report are not valid independent runtimes: the upstream timer keeps
running while agents wait for sequential post-run trace analysis.

## Per-game result

Every game used 81 actions because the upstream loop condition is
`action_counter <= MAX_ACTIONS` with `MAX_ACTIONS = 80`.

| Game | Levels | Score | Actions | Resets | Final state |
| --- | ---: | ---: | ---: | ---: | --- |
| ar25 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| bp35 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| cd82 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| cn04 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| dc22 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| ft09 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| g50t | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| ka59 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| lf52 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| lp85 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| ls20 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| m0r0 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| r11l | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| re86 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| s5i5 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| sb26 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| sc25 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| sk48 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| sp80 | 0 | 0.0 | 81 | 2 | `GAME_OVER` |
| su15 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| tn36 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| tr87 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |
| tu93 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| vc33 | 0 | 0.0 | 81 | 1 | `GAME_OVER` |
| wa30 | 0 | 0.0 | 81 | 0 | `NOT_FINISHED` |

## What the symbolic system did

Across the 25 games, Reflector recorded:

- 2,000 learned transitions;
- 1,794 schemas and 479 synthetic concepts;
- 206 schema reuses and 6,307 concept reuses;
- 411 causal and 983 temporal hypotheses;
- 461 failed experiments;
- 93,879 planner expansions;
- mean internal prediction accuracy of 0.604;
- zero level advances;
- zero learned procedures;
- zero accepted language operators.

These numbers expose the central failure. Reflector compresses and predicts
parts of its sensorimotor stream, but its abstractions are not yet connected
to goal discovery or successful control. High internal structure counts and
prediction accuracy are therefore not evidence of ARC competence.

## Recording defect discovered

The 25 recording files exist and their aggregate manifest SHA-256 is
`baab7d9faf05b1c410f8486c5fb48d602cbe81e667e892b8fbb0a6579acf95e3`.
However, all 2,025 recorded frames contain action ID `0`.

The official adapter converts `FrameDataRaw` to `FrameData` without preserving
`action_input`; the model default is then serialized as `RESET`. Consequently:

- the scorecard and agent traces remain valid evaluation evidence;
- the saved files preserve frames and outcomes;
- the files do **not** faithfully preserve chosen actions or explanations and
  must not be presented as exact gameplay replays.

This defect needs a regression test and a corrected rerun before the public
games are used in the web replay interface.

### Resolution

The adapter now preserves `action_input`, freezes gameplay duration before
post-run analysis, and has regression coverage for legal non-reset actions and
symbolic explanations. The faithful v14 recordings contain the actual action
coordinates and were used for the subsequent trajectory analysis. The original
v8 files remain explicitly invalid as action replays.

## Kaggle status

The exact frozen agent still passes the network-disabled Kaggle smoke test and
exports both intended artifacts:

- overlay SHA-256:
  `762b193ccc07655c845d52099bfdea692ae46cfbdaed32641d8e386fca57080b`
- notebook SHA-256:
  `d790782da5ecaac6fbddb6bcb1f3fa13a08b9164a00129a212b008215b16d850`

Thus the submission architecture is validated locally. Performance is not.
The 25 public games are development evidence, not a Kaggle leaderboard score;
only a committed Kaggle rerun can evaluate the separate 110 hidden games.

## Research consequence

The next accepted descendant should not be selected for producing more schemas,
concepts, compression, or synthetic-validation wins alone. It must demonstrate
causal improvement on the official public environments, beginning with at
least one reproducible level completion and a same-environment ablation showing
which mechanism caused it.

Official references:

- <https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data>
- <https://docs.arcprize.org/toolkit/list-games>
- <https://github.com/arcprize/ARC-AGI-3-Agents>
