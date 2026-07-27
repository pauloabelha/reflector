# Reflector

Reflector is a Kaggle-first platform for evolving purely symbolic agents on
ARC-AGI-3. It is built directly on the official
[ARC-AGI-3-Agents](https://github.com/arcprize/ARC-AGI-3-Agents) starter.

> Do not build a separate prototype and retrofit Kaggle compatibility later.
> Kaggle compatibility is the foundational architectural constraint from the
> first commit.

The first descendant is intentionally small. It converts an official ARC frame
into an immutable symbolic observation, selects only from the reported legal
actions, uses a deterministic rare-color centroid for complex click actions,
and runs with no LLM, internet, remote service, database, or web server.

## Verified baseline

The same `reflector.SymbolicPolicy` powers the official local adapter and the
generated Kaggle notebook. The baseline currently passes:

- the official `Arcade` local environment and `Swarm` lifecycle;
- five levels of the official toolkit's deterministic `bt11` fixture;
- a self-contained Kaggle overlay/notebook export;
- a clean subprocess with a disabled Linux network namespace;
- initialization, observation receipt, legal action selection, environment
  advancement, scorecard closure, and clean termination.

## Setup

Reflector requires Python 3.12, matching the current starter and toolkit.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

Run the permanent offline compatibility check:

```bash
.venv/bin/kaggle_smoke_test
```

Export the Kaggle artifacts:

```bash
.venv/bin/reflector-kaggle export --output dist
```

This produces:

- `dist/reflector-kaggle-overlay.zip`, the inference-only source overlay;
- `dist/reflector-kaggle-submission.ipynb`, a self-contained notebook that
  embeds that exact overlay and uses the competition-provided starter/wheels.

For a local official-harness run:

```bash
OPERATION_MODE=offline \
ENVIRONMENTS_DIR=tests/fixtures/official_toolkit \
RECORDINGS_DIR=recordings \
.venv/bin/python -c \
  'from agents import Swarm; Swarm("reflector", "http://localhost:8001", ["bt11"]).main()'
```

## Governing invariant

Every accepted agent descendant must remain directly exportable as an offline
ARC-AGI-3 Kaggle submission without architectural translation or manual
rewriting. Development-only evolution, analysis, persistence, and UI code may
consume the symbolic package but may never be imported by its Kaggle path.

See [KAGGLE.md](KAGGLE.md), [ARCHITECTURE.md](ARCHITECTURE.md),
[THEORY.md](THEORY.md), and [EVALUATION.md](EVALUATION.md).

## Status

The end-to-end Kaggle-compatible symbolic baseline exists. Deeper schema
induction, synthetic concepts, reflecting abstraction, epistemic compression,
population evolution, and the replay UI are subsequent evidence-driven layers;
they must preserve the invariant above.

## License

MIT. The retained official starter code is also MIT licensed.
