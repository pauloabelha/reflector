# ARC-AGI-3 harness

`reflector2.arc_harness` is a thin transport adapter between the public
`arc-agi` toolkit and Reflector-II. It contains no game IDs, action meanings,
policy rules, planner, model calls, or Reflector-I solver code.

For each toolkit observation it preserves the ordered frame packet as ordered
R2 supports. The terminal support—the state opened for the next action—is
observed by an isolated R2 runtime and supplies the before/after carrier for
`Runtime.learn_transition`; earlier render/animation supports remain ordered
in provenance rather than becoming fictitious agent transitions. Action IDs
remain opaque tokens of the form `arc-action:N`. A transition trace retains
the exact before observation, action ID and transport payload, successor
observation, reset/level/completion boundaries, native reward when present,
progress delta, and the resulting R2 morphism identity.

The controller samples uniformly from the legal action IDs exposed by the
current observation. Complex action payloads are sampled only from the
toolkit's transport schema and current grid bounds. `GAME_OVER` and
`NOT_PLAYED` are lifecycle boundaries and force the toolkit reset operation.
`WIN` ends the run. Per-game action and environment RNG streams are derived
from the master seed with SHA-256, so suite order does not affect replay.

The repository includes the 25 public games under `environment_files/`. Set up
the project and run the full local suite with:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/reflector2-arc \
  --expected-games 25 \
  --seed 0 \
  --max-transitions 80
```

The trace directory contains:

- `GAME.trace.jsonl`: ordered observations and compact transition provenance;
- `GAME.r2.jsonl`: native R2 observation, shadow, binding, truncation, and
  mapping events;
- `summary.json`: per-game progress, completion, official toolkit score,
  deterministic R2 counters, suite totals, and any errors.

By default, traces are written to the ignored `arc-traces/` directory and
toolkit scorecard data uses the ignored `recordings/` directory. Use
`--game ar25` for a narrow smoke test and `--omit-grids` when only support
digests and shapes are needed.
