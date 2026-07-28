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

An accepted population descendant is exported without policy translation:

```bash
.venv/bin/reflector-kaggle export \
  --config candidate.json --output dist
.venv/bin/reflector-kaggle smoke-test --config candidate.json
```

Run the current competition-readiness audit:

```bash
.venv/bin/reflector-prize-audit
```

For a local official-harness run:

```bash
OPERATION_MODE=offline \
ENVIRONMENTS_DIR=tests/fixtures/official_toolkit \
RECORDINGS_DIR=recordings \
.venv/bin/python -c \
  'from agents import Swarm; Swarm("reflector", "http://localhost:8001", ["bt11"]).main()'
```

Or produce one structured report containing the official scorecard, per-agent
wall time/action count/levels, and the full trace metrics:

```bash
.venv/bin/reflector official-run bt11 \
  --environments-dir tests/fixtures/official_toolkit \
  --recordings-dir /tmp/reflector-recordings
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

Run the latest preregistered synthetic mechanism benchmark:

```bash
.venv/bin/reflector validate --suite v3 --seed-start 60000 --seeds 30 \
  --output validation-v3-holdout.json
.venv/bin/reflector validate --suite v4 --seed-start 90000 --seeds 30 \
  --output validation-v4-holdout.json
.venv/bin/reflector validate --suite v5 --seed-start 120000 --seeds 30 \
  --output validation-v5-holdout.json
```

This benchmark compares the deployed policy with ablations and simple
baselines. It is explicitly not an ARC score; see
[`VALIDATION_V5.md`](VALIDATION_V5.md) for the latest frozen claim boundary and
criteria, and [`VALIDATION_RESULTS.md`](VALIDATION_RESULTS.md) for the original
falsification plus the v2–v5 confirmation results. V3 supports narrow
conditional accommodation; v4 supports executable transformation composition
and v5 supports bounded possible/impossible reachability in control under
identical training histories. None is evidence of general equilibration,
category-theoretic cognition, or official-game generalization.

Run a reproducible population evaluation (network isolation is on by default):

```bash
.venv/bin/reflector population-evaluate \
  /tmp/reflector-trace.json --db /tmp/reflector-experiments.sqlite
.venv/bin/reflector evolve \
  /tmp/reflector-trace.json --db /tmp/reflector-evolution.sqlite
.venv/bin/reflector evolution-ablations \
  --db /tmp/reflector-evolution.sqlite --experiment EXPERIMENT_ID
```

`evolve` uses deterministic mutations unless an OpenAI-compatible JSON endpoint
and model are explicitly supplied. Mutation providers can only propose
validated `MindConfig` field changes; they cannot inject code. Every candidate
is the same `SymbolicPolicy` used by Kaggle, executed twice in a clean
network-disabled process, stored with its parent, and compared by a Pareto
archive. Use `reflector lineage --db DB --experiment ID [--candidate ID]` to
inspect the archive or one ancestry chain.

Build and run the local replay/analysis console:

```bash
cd web && npm install && npm run build && cd ..
.venv/bin/reflector web /tmp/reflector-trace.json \
  --db /tmp/reflector-evolution.sqlite
```

Open `http://127.0.0.1:8765`. The TypeScript console renders the recorded ARC
board with play/pause/step controls, the action explanation, prediction versus
observed transition, persistent objects, facts, concepts, schemas, hypotheses,
dependency graph, language inventory, genealogy, structural diffs, regression
retention, and Pareto front. It contains no remote assets or telemetry. Its
branch tool replays a deployable configuration over fixed observations and
clearly avoids claiming counterfactual environment outcomes.

## Governing invariant

Every accepted agent descendant must remain directly exportable as an offline
ARC-AGI-3 Kaggle submission without architectural translation or manual
rewriting. Development-only evolution, analysis, persistence, and UI code may
consume the symbolic package but may never be imported by its Kaggle path.

See [KAGGLE.md](KAGGLE.md), [ARCHITECTURE.md](ARCHITECTURE.md),
[THEORY.md](THEORY.md), [EVALUATION.md](EVALUATION.md), and
[PRIZE_READINESS.md](PRIZE_READINESS.md).

## Status

The end-to-end Kaggle baseline now includes online schemas, causal and temporal
hypotheses, explicit experiment questions, bounded event-goal planning, and
utility-gated synthetic concepts. It now derives bounded spatial relations,
MDL-positive schema families and concept types, and evidence-gated symbolic
language versions, including a compositional ℤ₄ orientation operator when
repeated rotation evidence pays its cost. Accepted concepts become later schema
terms, language operators normalize later events, and family confidence feeds
the bounded planner. Evidence-backed translations now compile into explicit
operator objects used by a bounded spatial planner; the inference trace also
exposes represented inverses, finite modal reachability, and a typed comparison
graph with executable finite law checks. Development tooling measures recoverable
redundancy and counterfactual representation savings without claiming
unobservable action savings. It also provides serializable constrained
genomes, transformed trace holdouts, reproducible experiment manifests,
SQLite lineage, Pareto selection, optional provider-neutral mutation proposals,
and sandboxed population evaluation. Evidence-gated procedures and
context-sharing schema families now pass their preregistered synthetic v2
efficiency ablations. This is mechanism evidence, not an ARC score.
Drescher-faithful synthetic items, a full opportunistic composite-action
controller, broader relational languages, and true environment holdouts remain.
The first complete local replay and population-analysis UI is operational.

## License

Reflector-authored material is dual-licensed MIT-0 or CC BY 4.0. Retained
official starter material remains MIT licensed. See [LICENSE](LICENSE),
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and
[OPEN_SOURCE_AI.md](OPEN_SOURCE_AI.md).
