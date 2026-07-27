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
  population, mutations, sandbox, evolver, and CLI modules are development
  consumers and must remain outside that allowlist.
- `agents/templates/reflector_agent.py` is a thin official-starter adapter. It
  must delegate decisions to `reflector/`.
- `reflector/kaggle.py` owns export and compatibility verification. Generated
  notebooks are artifacts, not a second implementation.
- Evolver, LLM, database, API, and UI modules belong outside the inference
  overlay listed by `OVERLAY_FILES`.
- Never import OpenAI, LangChain, a web framework, a database driver, or a
  population manager from the Kaggle overlay.
- Do not hardcode solutions for public game IDs. Mechanisms may encode general
  priors only and must earn complexity through evaluation.

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
