# ARC-AGI-3 harness

`reflector2.arc_harness` is a thin transport adapter between the public
`arc-agi` toolkit and Reflector-II. It contains no game IDs, action meanings,
planner, model calls, or Reflector-I solver code. Action selection occurs only
at its final controller boundary and uses one of three generic policy modes.

For each toolkit observation it preserves the ordered frame packet as ordered
R2 supports. The terminal support—the state opened for the next action—is
observed by an isolated R2 runtime and supplies the before/after carrier for
`Runtime.learn_transition`; earlier render/animation supports remain ordered
in provenance rather than becoming fictitious agent transitions. Action IDs
remain opaque tokens of the form `arc-action:N`. A transition trace retains
the exact before observation, action ID and transport payload, successor
observation, reset/level/completion boundaries, native reward when present,
progress delta, and the resulting R2 morphism identity.

The policy modes are:

- `random` (default): sample uniformly from legal opaque action IDs;
- `local-schema`: rank consequences predicted by active transition schemas,
  without explanation assemblies or prospective commitments;
- `explanation`: construct a bounded competing set, rank its predicted
  consequences, and commit selected predictions as ordinary R2 shadows.

Every non-random decision starts from the same seeded random candidate, which
is retained as `baseline_top` in the decision trace. Unsupported actions
abstain and preserve that seeded ordering. Complex action payloads are sampled
only after the opaque action ID is chosen, using the toolkit's transport schema
and current grid bounds.

`GAME_OVER` and `NOT_PLAYED` are lifecycle boundaries and force the toolkit
reset operation. `WIN` ends the run. Per-game action and environment RNG
streams are derived from the master seed with SHA-256, so suite order does not
affect replay.

The repository includes the 25 public games under `environment_files/`. Set up
the project and run the full local suite with:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/reflector2-arc \
  --policy random \
  --expected-games 25 \
  --seed 0 \
  --max-transitions 80
```

Use `--policy local-schema` or `--policy explanation` to select an experimental
controller. `--max-explanations N` bounds the explanation beam and defaults to
8. For a matched three-policy run over isolated runtimes:

```bash
.venv/bin/reflector2-explanations \
  --game ar25 \
  --seed 0 \
  --max-transitions 30 \
  --workers 1 \
  --output-dir experiments/minimal-explanation-driven-control/rerun
```

The trace directory contains:

- `GAME.trace.jsonl`: ordered observations and compact transition provenance;
- `GAME.r2.jsonl`: native R2 observation, shadow, binding, truncation, and
  mapping events;
- `summary.json`: per-game progress, completion, official toolkit score,
  deterministic R2 counters, suite totals, and any errors.

`local-schema` and `explanation` traces additionally contain an
`explanation-decision` event before the corresponding transition. It records
the seeded baseline, selected opaque action, complete action ranking, predicted
effect signatures, and whether the controller changed the action.
`explanation` may then emit `explanation-resolution` after the transition with
shadow reification/refutation and ambiguity reduction. Per-game runtime
reports include explanation construction, commitment, calibration, action
change, and progress-after-change metrics. Random reports intentionally omit
that section.

By default, traces are written to the ignored `arc-traces/` directory and
toolkit scorecard data uses the ignored `recordings/` directory. Use
`--game ar25` for a narrow smoke test and `--omit-grids` when only support
digests and shapes are needed.
