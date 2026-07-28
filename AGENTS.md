# Working on Reflector

## Non-negotiable invariant

Every accepted symbolic-agent descendant must be directly exportable as an
offline ARC-AGI-3 Kaggle submission without translation or manual rewriting.
Kaggle compatibility is a design input, never a release-time retrofit.

## Required checks

Before accepting an inference-path change, run:

```bash
.venv/bin/pytest
.venv/bin/kaggle_smoke_test
.venv/bin/reflector-kaggle export --output dist
```

The smoke test must continue to run the exported overlay in a new directory and
network namespace, load an official toolkit environment, choose a legal action,
advance it, close the scorecard, and exit.

## Boundaries

- The Kaggle allowlist in `reflector/kaggle.py` is the shared symbolic
  inference closure. Keep it deterministic, typed, serializable, and free of
  development services. Evaluation, compression, transforms, experiments,
  population, mutations, sandbox, evolver, web API, frontend, and CLI modules
  are development consumers and must remain outside that allowlist.
- `agents/templates/reflector_agent.py` is a thin official-starter adapter. It
  must delegate decisions to `reflector/`.
- `reflector/kaggle.py` owns export and compatibility verification. Generated
  notebooks are artifacts, not a second implementation.
- Evolver, LLM, database, API, and UI modules belong outside the inference
  overlay listed by `OVERLAY_FILES`.
- Never import OpenAI, LangChain, a web framework, a database driver, or a
  population manager from the Kaggle overlay.
- Web views must derive from trace/API evidence. Never add fabricated
  dashboard metrics, and keep trace-only branches explicitly distinct from
  environment rollouts.
- Do not hardcode solutions for public game IDs. Mechanisms may encode general
  priors only and must earn complexity through evaluation.
- A schema family, concept type, or language operator must retain member
  evidence, raw/compiled description cost, positive utility, and dependency
  edges. Do not promote a symbolic label or regex match by itself.
- Never score a transition using predictions learned from that same transition.
  Runtime and allocation measurements are diagnostics and must not be presented
  as deterministic across machines.
- An accepted abstraction must remain on an operative path: compiled concept
  terms, normalized language events, or bounded planning evidence. Preserve
  the raw evidence and do not claim cross-game transfer from internal reuse.
- Every selected descendant must be exported by serializing its validated
  `MindConfig` into the notebook. Never copy or rewrite candidate policy logic.
- Prize claims require the current rules snapshot, a public participant-owned
  repository, a public Kaggle notebook, a scored rerun, and held-out public
  evaluation. A fixture or smoke-test score is never a leaderboard score.

## Official compatibility

Preserve the official `Agent.is_done(frames, latest_frame)` and
`Agent.choose_action(frames, latest_frame)` entry points, `Swarm`, `Arcade`,
`FrameData`, `GameAction`, and competition gateway path. If an upstream
interface changes, update the audit in `KAGGLE.md`, the exporter, and the smoke
test together before doing research-layer work.

## Evidence standard

Do not label an LLM-generated name as a synthetic concept, epistemic
compression, or reflecting abstraction. Record its definition, evidence,
dependencies, counterfactual utility, complexity cost, and measurable effect.

## Persistent evolution protocol

`PLAN.md` is the durable continuation state for this repository. At the start
of every Codex session:

1. read this file and `PLAN.md` completely;
2. inspect the worktree, current branch, recent commits, configured remotes,
   accepted candidate, and referenced result artifacts;
3. resume the first unfinished plan item unless the user explicitly changes
   direction;
4. update `PLAN.md` whenever evidence changes the accepted baseline, active
   hypothesis, next experiment, or blocker;
5. update `REAL_GAMES_REPORT.md` whenever a real-game evaluation or Kaggle
   submission changes;
6. leave the long-running goal active until Reflector scores competitively on
   the actual Kaggle evaluation—not merely on fixtures or the 25 development
   games.

The default research loop is:

1. analyze recorded failures without reading hidden evaluation data;
2. state a general symbolic hypothesis and its falsifier;
3. implement it behind the shared `MindConfig` inference path;
4. add a unit-level structural test and verify it on recorded observations;
5. run a narrow official-harness target test;
6. reject regressions or run the accepted-win promotion gate;
7. freeze the exact source commit, run all 25 official public-development
   games, export the same candidate, and run the network-disabled Kaggle smoke;
8. promote only with complete evidence, document causal attribution, commit,
   and push to the participant-owned repository;
9. begin the next failure analysis.

Do not silently stop at a promising target result. A candidate is accepted
only after it preserves every accepted real-game completion, passes the full
suite and Kaggle packaging checks, and has a permanent report. Keep negative
descendants and ablations as evidence.

`REAL_GAMES_REPORT.md` is the only root-level real-game score report. Raw,
immutable scorecards belong under `reports/`. Always distinguish:

- local official public-development score;
- Kaggle public-leaderboard score;
- Kaggle private-leaderboard score;
- target-only experimental results.

Never infer a leaderboard score from a local run. Record “not submitted” or
“unavailable” when that is the truth. For each gain, identify the parent,
mechanism, controlled comparison, affected game/level, action efficiency, and
remaining limitation.
