# Learned R2 Relevance Bridge

This directory contains the preregistered learned-relevance experiment. No
files under `src/reflector2` are modified.

`frozen-arms.json` pins the three control implementations to explanation-branch
commit `f2e5d69`; the runner verifies their source hashes before doing work.

The included `fixtures/` streams are synthetic mechanical checks only. They
must never be reported as ARC evidence or used for a scientific verdict.

Extract evidence from chronological baseline traces that include grids:

```bash
PYTHONPATH=src python3 experiments/learned-r2-relevance-bridge/collect_evidence.py \
  --trace path/to/baseline-a.trace.jsonl \
  --trace path/to/baseline-b.trace.jsonl \
  --output path/to/learning.jsonl \
  --require-positive
```

The extractor reconstructs each transition schema from its recorded
before/after grids and opaque action. It does not trust a stored consequence
label. Both experiment traces and official ARC toolkit `recording.jsonl` files
are accepted. Traces produced with `--omit-grids` cannot be used.

Run the mechanical screen:

```bash
PYTHONPATH=src python3 experiments/learned-r2-relevance-bridge/run_experiment.py \
  --learning-stream experiments/learned-r2-relevance-bridge/fixtures/mechanical-learning.jsonl \
  --held-out-stream experiments/learned-r2-relevance-bridge/fixtures/mechanical-held-out.jsonl \
  --output-dir /tmp/reflector2-relevance-mechanical
```

Run experiment-local tests:

```bash
python3 -m pytest -q experiments/learned-r2-relevance-bridge/tests
```

For a real intervention, replace both fixture paths with preregistered,
disjoint public trajectory streams and add:

```bash
--run-live --game <public-game-id> --game <public-game-id>
```

Use `--verify-live-replay` only after deciding to spend a second identical
public cohort. Without verified live replay the verdict cannot be `PROMOTE`.

## Evidence record

Each JSONL record has:

- `sequence`: strict chronological position;
- `event_id`: immutable provenance key;
- `context_id`: distinct-support identity (hashed before R2 evidence use);
- `trajectory_id`: used only to constrain Null A and report concentration;
- `pairing_stratum`: preregistered structural matching stratum for Null B;
- `binding_key`: structural realization fingerprint, used only to classify
  transfer as class 1 versus class 2;
- `consequence`: the observed `Change`/`Preserve` atoms;
- `progress_delta`: legally observed progress after the transition;
- `opaque_action_id`: optional audit field, never admitted to a relevance
  schema, match, or ranking;
- `source`: provenance label.

The runner writes `frozen-relevance-schemas.json`, `summary.json`, and (for
live runs) per-arm traces. Every prospective relevance commitment appears in
the trace before its corresponding transition and resolution.
Forecast receipts reference their value-bearing frozen schema by exact hash and
include ordered evidence counts/digests. The snapshot stores the corresponding
full support and contradiction event-ID lists once, avoiding redundant trace
inflation without weakening provenance.
