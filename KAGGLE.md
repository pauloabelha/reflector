# Kaggle contract

Audit date: 2026-07-31.

Current accepted export: v99k
`candidate-ddf2529a2bae5601`, local public-development score
`21.632592714022195 / 100`. Exact SHA-256 values:

- candidate:
  `fa2c05667cca8078123d0e517f7918a9a701a8e1dfa9d6dfb35e0332d92bbc58`;
- overlay:
  `0b27853b2e428f0a8aee6219b7cf90f2c8d559f5ff435e3b32c591e9d5eefbef`;
- notebook:
  `dd93c904b2a44ee7ba53a6e591c51cfd64e0e595bb27751a596a063edf3a3143`.

This is local evidence, not a Kaggle public or private score.

Submission status, 2026-07-31 UTC:

- private notebook `pauloabelha/reflector-arc-agi-3-v84m` version 1 completed
  successfully and emitted `submission.parquet`;
- its competition submission request returned HTTP 400 because v74 submission
  `55123277` had already consumed the one-per-day allowance;
- no v84m competition submission ID exists yet;
- v99k is now the accepted local package;
- private notebook `pauloabelha/reflector-arc-agi-3-v92` version 1 completed
  successfully and emitted `submission.parquet`;
- its competition submission request also returned HTTP 400 while v74 remains
  pending, so no v92 competition submission ID exists yet;
- private notebook `pauloabelha/reflector-arc-agi-3-v94b` version 1 completed
  successfully and emitted `submission.parquet`;
- its competition submission request returned HTTP 400 while v74 remains
  pending and occupies the UTC daily allowance, so no v94b submission ID
  exists yet;
- the exact v97 export passes two deterministic exports, both network-disabled
  smoke paths, and the technical prize audit;
- private notebook `pauloabelha/reflector-arc-agi-3-v97` version 1 completed
  successfully and emitted `submission.parquet`;
- its competition submission request returned HTTP 400 while v74 remains
  pending and occupies the UTC daily allowance, so no v97 submission ID
  exists; resubmit this already completed version unchanged when the slot
  clears;
- the exact v98 candidate exports byte-identically twice, both
  network-disabled smoke paths pass, and the technical prize audit reports
  `technical_ready: true`;
- private notebook `pauloabelha/reflector-arc-agi-3-v98` version 1 completed
  successfully and emitted a 2,648-byte `submission.parquet`, SHA-256
  `71bfd543030e339d87bd9ff744d466218398a1259650b2c255626d27049c88bb`;
- the v98 competition submission request returned HTTP 400 because v74 had
  already consumed the UTC daily allowance; Kaggle created no v98 submission
  ID, so submit completed version 1 unchanged after the quota resets;
- the exact v99k candidate exports byte-identically twice, both
  network-disabled smoke paths pass, and the technical prize audit reports
  `technical_ready: true`;
- private notebook `pauloabelha/reflector-arc-agi-3-v99k` version 1 completed
  successfully and emitted a 2,648-byte `submission.parquet`, SHA-256
  `71bfd543030e339d87bd9ff744d466218398a1259650b2c255626d27049c88bb`;
- the exact v99k competition request returned HTTP 400 because v74 submission
  `55123277` had consumed the UTC daily allowance; the subsequent listing
  contains only v65b and v74, so no v99k submission ID exists;
- submit completed v99k notebook version 1 unchanged after the allowance
  resets;
- v74 submission `55123277` has now completed with public score `0.02`;
- historical v65b submission `55113224` is complete with Kaggle public score
  `0.02`; the private score remains unavailable.

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

## Strict public-environment evaluation

Once the accepted `environment_files/` data is available locally:

```bash
.venv/bin/reflector official-public-run \
  --environments-dir /path/to/environment_files \
  --recordings-dir /tmp/reflector-public-recordings \
  --output official-public-evaluation.json
```

The command discovers versioned `metadata.json` files exactly as the toolkit
does, reduces versions to unique game IDs, and requires the
`public_development_games` count in the dated rules snapshot—currently 25. It
hashes each metadata file and the canonical inventory, records the source
commit and deployed `MindConfig`, invokes the official `Swarm` once over every
game, and fails if agent-report coverage is incomplete. A fixture-only checkout
therefore fails before evaluation instead of accidentally presenting `bt11` as
a public-suite result.

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

The inference allowlist includes `reflector/core/abstraction.py`. Its
schema-family, concept-type, and language-reflection passes operate only on
bounded in-memory symbolic stores; they add no package, network, database, or
filesystem dependency. The rest of the canonical inference closure lives in
`reflector/core/` and `reflector/runtime/`; development-only `research/` and
`evolution/` packages are excluded.

## Prize eligibility

Technical Kaggle compatibility does not establish prize eligibility. Run
`.venv/bin/reflector-prize-audit` and complete the manual account, public
repository, public notebook, identity, data-security, and full-rerun gates in
[PRIZE_READINESS.md](PRIZE_READINESS.md). Reflector-authored material is
available under MIT-0 or CC BY 4.0, while retained starter material remains
MIT; provenance and the absence of neural weights are documented in
[OPEN_SOURCE_AI.md](OPEN_SOURCE_AI.md).
