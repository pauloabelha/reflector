# Kaggle contract

Audit date: 2026-07-27.

Reflector began from the official
[`arcprize/ARC-AGI-3-Agents`](https://github.com/arcprize/ARC-AGI-3-Agents)
repository at commit `10213de83f01df0ef4f0149ee9f8408dcc3772fb`.
The toolkit audit used
[`arcprize/ARC-AGI`](https://github.com/arcprize/ARC-AGI) commit
`f12822c4d550121c35a275008d964afbbed47d2f` and package version `0.9.9`.

## Authoritative interface

The competition data mount contains:

- `ARC-AGI-3-Agents/`, the official agent starter;
- `arc_agi_3_wheels/`, wheels used for offline installation;
- `environment_files/`, the 25 public development environments.

An official-starter agent implements:

```python
is_done(frames, latest_frame) -> bool
choose_action(frames, latest_frame) -> GameAction
```

`Swarm` opens one scorecard, makes one agent/environment per game, runs them,
then closes the scorecard. Kaggle forces remote/competition behavior through a
local evaluation gateway. During a rerun, the notebook must wait for
`http://gateway:8001/api/games`, copy the read-only starter to
`/kaggle/working`, set `OPERATION_MODE=online`, and run the official `main.py`.
It must not call `three.arcprize.org`.

The submission is a committed Kaggle notebook with internet disabled. Ordinary
notebook commits emit `/kaggle/working/submission.parquet`; competition reruns
are detected through `KAGGLE_IS_COMPETITION_RERUN` and interact with the
gateway. Reflector's generated notebook follows this exact structure and
installs only from the competition wheel directory.

## Action protocol

- `RESET` is action id `0`.
- `ACTION1` through `ACTION5` are simple actions.
- `ACTION6` is complex and requires integer `x` and `y` coordinates in
  `[0, 63]`.
- `ACTION7` is an additional simple action.
- An environment reports its currently available actions after every step; the
  set may change.
- `NOT_PLAYED`/`NOT_STARTED` and `GAME_OVER` require reset.
- `WIN` terminates that game.

Frames are stacks of grids up to 64×64 with integer values from 0 through 15.
Reflector canonicalizes the reported legal action set and never samples the
global enum.

## Competition mode and scoring

The official toolkit's competition mode permits one `make` call per
environment and one scorecard; game resets become level resets, and in-flight
score retrieval is disabled. The score is Relative Human Action Efficiency:
completed level score is the squared human/agent action ratio with a 1.15 cap,
game scores are weighted by 1-indexed level, and the total is the mean over all
games. Unplayed games therefore matter.

The current code-competition limit is nine hours for either CPU or GPU
notebooks, with internet disabled and a 20,480 MB submission limit. Kaggle has
added RTX 6000 `g4-standard-48` machines to this competition's pool. Reflector's
baseline is CPU-only, contains no model artifacts, and completes its smoke run
in under one second, but only a full 110-game Kaggle rerun establishes
competition runtime compliance. No later component may assume that unused
headroom is stable.

Kaggle permits one submission per day, two final submissions, and teams of at
most eight. The safety cutoff for accepting the rules is October 26, 2026 at
11:59 UTC, the team-merger deadline is October 26 at 23:59 UTC, and final
submissions close November 2 at 23:59 UTC. See
[PRIZE_READINESS.md](PRIZE_READINESS.md) and refresh the dated rule snapshot
before each submission.

Primary references:

- [Kaggle competition data and scoring](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data)
- [Official toolkit](https://github.com/arcprize/ARC-AGI)
- [Official agents starter](https://github.com/arcprize/ARC-AGI-3-Agents)
- [Official scoring methodology](https://docs.arcprize.org/methodology)
- [Official action-space documentation](https://docs.arcprize.org/toolkit/list-actions)

## Export

```bash
.venv/bin/reflector-kaggle export --output dist
```

The notebook embeds the overlay bytes generated from the same checked-out
`reflector` package used locally. It does not paste or reimplement policy logic.
To export an accepted evolved descendant, pass either its `MindConfig` JSON or
serialized `Candidate` JSON:

```bash
.venv/bin/reflector-kaggle export \
  --config candidate.json --output dist
.venv/bin/reflector-kaggle smoke-test --config candidate.json
```

The config is validated and embedded as `REFLECTOR_CONFIG_JSON`; the official
adapter loads it through the same `SymbolicPolicy` used in experiments.
Upload or copy the generated notebook into the competition, attach the
competition data source, keep internet disabled, commit it, and submit that
committed version.

## Permanent smoke test

```bash
.venv/bin/kaggle_smoke_test
```

The command:

1. builds the inference overlay;
2. extracts it over a clean official-starter-shaped directory;
3. copies the official toolkit's deterministic `bt11` fixture;
4. starts a fresh Linux user and network namespace with `unshare -Urn`;
5. initializes `Arcade` in explicit offline mode;
6. receives an observation;
7. verifies the selected action is in `available_actions`;
8. advances the official environment;
9. closes the scorecard and exits.

CI also validates that the overlay equals the explicit inference allowlist,
excludes the evolver, mutation providers, SQLite store, sandbox, and other
development services, and retains all gateway, mount, rerun, agent, and
parquet contract markers in the generated notebook.

The inference allowlist includes `reflector/abstraction.py`. Its schema-family,
concept-type, and language-reflection passes operate only on bounded in-memory
symbolic stores; they add no package, network, database, or filesystem
dependency.

## Prize eligibility

Technical Kaggle compatibility does not establish prize eligibility. Run
`.venv/bin/reflector-prize-audit` and complete the manual account, public
repository, public notebook, identity, data-security, and full-rerun gates in
[PRIZE_READINESS.md](PRIZE_READINESS.md). Reflector-authored material is
available under MIT-0 or CC BY 4.0, while retained starter material remains
MIT; provenance and the absence of neural weights are documented in
[OPEN_SOURCE_AI.md](OPEN_SOURCE_AI.md).
