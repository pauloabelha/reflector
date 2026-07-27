# Reflector

Reflector is a Kaggle-first platform for evolving purely symbolic agents on
ARC-AGI-3. It is built directly on the official
[ARC-AGI-3-Agents](https://github.com/arcprize/ARC-AGI-3-Agents) starter.

> Do not build a separate prototype and retrofit Kaggle compatibility later.
> Kaggle compatibility is the foundational architectural constraint from the
> first commit.

The first learning descendant converts official frames into connected objects
with persistent identities, derives facts and events, induces empirical
context + action → result schemas, attributes action effects, and retains
synthetic concepts only when repeated evidence pays their complexity cost. It
selects only reported legal actions and runs with no LLM, internet, remote
service, database, or web server.

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

Generate, replay, evaluate, and compare deterministic traces:

```bash
.venv/bin/reflector trace-demo --output /tmp/reflector-trace.json
.venv/bin/reflector replay /tmp/reflector-trace.json
.venv/bin/reflector evaluate /tmp/reflector-trace.json
.venv/bin/reflector compare /tmp/reflector-trace.json
.venv/bin/reflector compression /tmp/reflector-trace.json
.venv/bin/reflector counterfactual /tmp/reflector-trace.json
.venv/bin/reflector ablations /tmp/reflector-trace.json
.venv/bin/reflector graph /tmp/reflector-trace.json
```

Run a reproducible population evaluation (network isolation is on by default):

```bash
.venv/bin/reflector population-evaluate \
  /tmp/reflector-trace.json --db /tmp/reflector-experiments.sqlite
.venv/bin/reflector evolve \
  /tmp/reflector-trace.json --db /tmp/reflector-evolution.sqlite
```

`evolve` uses deterministic mutations unless an OpenAI-compatible JSON endpoint
and model are explicitly supplied. Mutation providers can only propose
validated `MindConfig` field changes; they cannot inject code. Every candidate
is the same `SymbolicPolicy` used by Kaggle, executed twice in a clean
network-disabled process, stored with its parent, and compared by a Pareto
archive. Use `reflector lineage --db DB --experiment ID [--candidate ID]` to
inspect the archive or one ancestry chain.

## Governing invariant

Every accepted agent descendant must remain directly exportable as an offline
ARC-AGI-3 Kaggle submission without architectural translation or manual
rewriting. Development-only evolution, analysis, persistence, and UI code may
consume the symbolic package but may never be imported by its Kaggle path.

See [KAGGLE.md](KAGGLE.md), [ARCHITECTURE.md](ARCHITECTURE.md),
[THEORY.md](THEORY.md), and [EVALUATION.md](EVALUATION.md).

## Status

The end-to-end Kaggle baseline now includes online schemas, causal and temporal
hypotheses, explicit experiment questions, bounded event-goal planning, and
utility-gated synthetic concepts. Development tooling measures recoverable
redundancy and counterfactual representation savings without claiming
unobservable action savings. It also provides serializable constrained
genomes, transformed trace holdouts, reproducible experiment manifests,
SQLite lineage, Pareto selection, optional provider-neutral mutation proposals,
and sandboxed population evaluation. Richer relations, hierarchy/language
reflection, true environment holdouts, and the replay UI remain.

## License

MIT. The retained official starter code is also MIT licensed.
