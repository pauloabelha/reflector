# ARC-AGI-3 public-game test report

Test date: 2026-07-28

Machine-readable evidence:
[`reports/public-game-evaluation-2026-07-28.json`](reports/public-game-evaluation-2026-07-28.json)

## Result

**BLOCKED — no official 25-game score was produced.**

The official competition data is not present locally. Both permitted remote
access paths rejected unauthenticated access:

- the Kaggle competition-data download returned HTTP 401;
- the ARC-AGI Toolkit game-discovery API returned HTTP 401.

The repository contains one deterministic `bt11` toolkit fixture. The strict
public evaluator found 1 rather than 25 unique game IDs and exited before
playing or writing a result. This is the intended anti-overclaiming behavior.

## Requirements verified

The official ARC-AGI-3 competition data page defines:

- 25 downloadable public development environments in `environment_files`;
- frames up to 64×64 and legal actions `RESET`, `ACTION1`–`ACTION7`, with
  `ACTION6` carrying coordinates;
- completion-and-efficiency scoring;
- a separate set of 110 unseen evaluation games, split equally between the
  public and private Kaggle leaderboards.

Reflector's `official-public-run` inventories `metadata.json` files, requires
exactly 25 unique base game IDs, hashes the inventory, runs every game through
the official `Swarm` in offline mode, and writes a report only when all 25
agent results are present.

## Checks completed while data is unavailable

| Check | Result | Scope |
| --- | --- | --- |
| Strict 25-game inventory gate | PASS | Rejected the 1-game fixture with exit code 2 |
| Network-disabled packaged Kaggle smoke | PASS | Initialized, received an observation, chose legal action 3, advanced, and exited |
| Kaggle overlay and notebook export | PASS | Both submission artifacts were generated successfully |
| Official-harness `bt11` fixture | PASS | Score 100; 5 levels; 72 actions; 1.52 seconds |
| Competition technical audit | PASS | `technical_ready=true` |
| Prize/public-evaluation audit | NOT COMPLETE | `prize_ready=false`; account, data, rerun, and publication remain manual |

The `bt11` result is compatibility evidence only. It is not a public-suite
benchmark and must not be reported as one.

The checkout was at commit
`cfba2db23ef08913d967f918475f816746d1225f`, with uncommitted concept-lifecycle
inference work present. Before the definitive run, the selected agent revision
must be frozen and its worktree state recorded unambiguously.

## Exact unblock and run

Join the Kaggle competition, accept its rules, download the competition data,
and make its `environment_files` directory available locally. Then run:

```bash
.venv/bin/reflector official-public-run \
  --environments-dir /path/to/environment_files \
  --recordings-dir /tmp/reflector-public-recordings \
  --output reports/official-public-evaluation.json
```

The command itself refuses incomplete coverage. A real leaderboard result
still requires exporting and committing the offline Kaggle notebook because
the local 25-game suite is distinct from Kaggle's 110 hidden games.

Official references:

- <https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data>
- <https://docs.arcprize.org/toolkit/list-games>
- <https://github.com/arcprize/ARC-AGI-3-Agents>
