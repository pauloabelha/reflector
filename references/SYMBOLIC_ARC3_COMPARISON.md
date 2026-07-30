# Fair comparison of symbolic ARC-AGI-3 agents

## Bottom line

As of 29 July 2026, there is no public evidence of a strong purely symbolic
agent on the current hidden ARC-AGI-3 Kaggle evaluation. The most relevant
published symbolic method is graph-frontier exploration from the 2025 Preview.
Its official result was 3.64%, 12 levels, zero full games, and 278,158 actions.
That is useful evidence about an algorithmic family, but it is not
apples-to-apples with Reflector's local 2026 public-development result of
4.2992976365/100, 16/183 levels, zero full games, and 10,000 actions.

The score numbers must not be ranked directly. They use different games,
evaluation vintages, and budgets. Reflector is dramatically more
action-bounded, but is also heavily developed against its 25 visible games.
Only a paired run can answer which method is stronger on those games; only
Kaggle can test hidden transfer.

## Taxonomy

An agent is **purely symbolic** here only when every inference-time state,
update, proposal, and action-selection operation is an inspectable discrete
algorithm. Handwritten perception and numeric statistics are allowed. Neural
embeddings, learned neural value functions, and LLM calls are not.

Report four categories separately:

1. Pure symbolic: object rules, graphs, search, programs, explicit hypotheses.
2. Non-LLM learned: CNN/RNN/world-model/RL agents without language models.
3. Hybrid neuro-symbolic: explicit graphs or programs plus neural ranking.
4. LLM/coding agents: any inference-time language-model call, even when the
   resulting world model is symbolic.

The 2025 field gives three useful reference points:

| Agent | Category | Preview evidence | Main mechanism |
| --- | --- | ---: | --- |
| Explore It Till You Solve It | Pure symbolic | 3.64%; 12 levels; 0 games; 278,158 actions | Segmented-frame graph and shortest paths to untested frontiers |
| Blind Squirrel | Hybrid | 6.71%; 13 levels; 1 game; 109,108 actions | State graph, pruning, learned ResNet state-action values |
| StochasticGoose | Non-LLM neural | 12.58%; 18 levels; 2 games; 255,964 actions | Learned action/click affordance prediction |

These were three-game hidden Preview results, not 2026 Kaggle results.
GuidedRandom is another symbolic/stochastic reference, but its Preview result
should be treated as a weaker control rather than a target.

## The paired protocol

Freeze before running:

- exact environment inventory and metadata hashes;
- agent source commit and configuration;
- action budget per game;
- random seeds and deterministic/nondeterministic classification;
- state reset and cross-level memory rules;
- scorer version and scoring formula;
- whether any public game was inspected, trained on, or used for mutation.

Use the official offline toolkit and run each game in a fresh process. The
primary comparison uses all 25 current public-development games and exactly 400
actions per game. No method may use routes, game IDs, per-game switches, human
solutions, or information from another agent's run. A method whose native
budget is larger also receives a separately labeled budget curve at
80/200/400/1,000/4,000 actions; that curve diagnoses sample efficiency but
cannot replace the 400-action comparison.

Report, in this order:

1. Full games beaten / games evaluated.
2. Levels completed / total levels.
3. Official RHAE score.
4. Actions per completed level and total actions.
5. Per-game paired differences, not only an aggregate.
6. Deterministic rerun agreement or seed distribution.
7. Wall time and peak memory.
8. Public-development, Kaggle-public, and Kaggle-private results in separate
   columns.

For stochastic systems, use at least ten preregistered seeds for targeted
experiments and report median, interquartile range, and best only as a
diagnostic. A promotion claim uses the median and must not lose an already
solved game. For deterministic systems, rerun every claimed new level twice.

Because the 25 public games are visible and have shaped Reflector, the paired
public comparison measures engineering progress, not general intelligence.
The decisive test is a frozen Kaggle package evaluated on the 55 public-hidden
and 55 private-hidden games. Kaggle does not provide a symbolic-only category;
all architectures share the same completion and efficiency metric.

## Controls to run

The minimum useful ladder is:

| Control | Question isolated |
| --- | --- |
| Seeded legal random | Are gains beyond chance? |
| Deterministic least-tried legal action | Does action balancing suffice? |
| Object-action frontier | Does grounded click proposal help? |
| Raw-frame graph frontier | Does state memory and return-to-frontier help? |
| Nuisance-reduced object/frame graph | Does symbolic state abstraction help? |
| Accepted Reflector v40 | Do causal hypotheses, schemes, and transfer add value? |

The repository now contains a research-only
`object-graph-frontier-v1` control in
`reflector/research/symbolic_controls.py`. It uses connected monochrome
components, conservative edge-strip normalization, an explicit transition
graph, and breadth-first paths to untested state-action frontiers. It is
intentionally outside the deployed runtime; copying it into a candidate would
require a separate promotion gate.

### First paired result

The complete 25-game, 400-action run produced:

| Agent | Games | Levels | RHAE / 100 | Actions |
| --- | ---: | ---: | ---: | ---: |
| Accepted Reflector v40 | 0/25 | 16/183 | 4.2992976365 | 10,000 |
| Object/frame graph frontier v1 | 0/25 | 1/183 | 0.0003283918 | 10,000 |

The control's only progress was `vc33` level 1, reproduced exactly in a second
run. Its more diagnostic measurements were 5,130 distinct states, 9,185
changed transition targets, and only 203 shortest-path frontier returns. The
graph rarely became a stable reusable map. The next control should therefore
change the state and effect representation—not merely tune click salience or
search order. It should cluster observations by persistent objects,
controllability, achieved relational effects, and hidden phase hypotheses,
then invalidate clusters through intervention evidence.

Run a full paired control with:

```bash
.venv/bin/python -m reflector.research.symbolic_control_eval \
  --environments-dir /home/pauloabelha/arc-agi-3-public-games-2026/environment_files \
  --recordings-dir /tmp/reflector-symbolic-control \
  --output reports/symbolic-object-graph-control-400.json \
  --action-budget 400
```

## Decision rule

Do not graft graph exploration into Reflector merely because it wins levels.
Promote a mechanism only if a paired ablation shows that it:

- adds a level or improves RHAE under the same budget;
- preserves all accepted solved games;
- reduces, rather than inflates, distinct nuisance states per causal state;
- produces a reusable causal transition or option, not a game-ID exception;
- survives exact reruns and Kaggle export.

The most informative expected result is not “graph good” or “Reflector good.”
It is a per-game decomposition: where frontier search wins through coverage,
where Reflector wins through structural transfer, and where both exhaust 400
actions. The intersection identifies the missing causal-state and option layer.

## Sources

- [ARC-AGI-3 scoring methodology](https://docs.arcprize.org/methodology)
- [ARC-AGI-3 Preview: 30-Day Learnings](https://arcprize.org/blog/arc-agi-3-preview-30-day-learnings)
- [Graph-Based Exploration for ARC-AGI-3](https://arxiv.org/abs/2512.24156)
- [ARC-AGI-3 2026 competition](https://arcprize.org/competitions/2026/arc-agi-3)
- [Milestone Prize #1](https://arcprize.org/blog/arc-prize-2026-milestone-1)
