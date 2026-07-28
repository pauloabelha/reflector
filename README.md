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

## Live score status

Last verified: 2026-07-28

> **Plain-language result:** Reflector has fully beaten **0 of 25 games**.
> It has solved **5 of 183 levels across 4 games**. All 25 games were
> evaluated; “25/25 evaluated” does not mean “25/25 beaten.”

| Metric | Accepted v21 result |
| --- | ---: |
| Complete games beaten | **0 / 25** |
| Games with at least one solved level | **4 / 25** |
| Levels solved | **5 / 183** |
| Official local score | **0.8359967620 / 100** |
| Games evaluated | **25 / 25** |
| Kaggle submissions | **0** |

The `0.8359967620` result is about **0.836% of the 100-point scale**, not
83.6%. It is a reproducible score on the known local public-development games,
not a Kaggle public-leaderboard score. The v21 package is submission-ready, but
hidden public and private scores remain unavailable until an actual submission.

The current v22 experiment has solved three levels of `ft09` in a target-only
run. It is not accepted because it has not passed the regression gate, full
25-game evaluation, and packaging checks.

See the canonical [real-games scorecard](REAL_GAMES_REPORT.md) for per-game
actions, causal mechanism attribution, evidence hashes, and the distinction
between local and Kaggle scores. This table and that report must be updated
together whenever a candidate is promoted or a Kaggle submission changes
state.

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

After attaching the accepted 25-game public data, run the strict coverage path:

```bash
.venv/bin/reflector official-public-run \
  --environments-dir /path/to/environment_files \
  --recordings-dir /tmp/reflector-public-recordings \
  --output official-public-evaluation.json
```

This inventories official metadata, requires exactly the rule-snapshot game
count, hashes every metadata file and the complete manifest, runs every game
through the unchanged official `Swarm`, and refuses to write a successful
report unless every game has an agent result.

The complete score history is recorded in
[`REAL_GAMES_REPORT.md`](REAL_GAMES_REPORT.md). Reflector progressed from v8's
zero-level result to v21's five levels across four public-development games.
Kaggle compatibility is proven locally; competitive hidden performance is not.

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
.venv/bin/reflector validate --suite v6 --seed-start 150000 --seeds 30 \
  --output validation-v6-holdout.json
.venv/bin/reflector validate --suite v7 --seed-start 180000 --seeds 30 \
  --output validation-v7-holdout.json
.venv/bin/reflector validate --suite v8 --seed-start 210000 --seeds 30 \
  --output validation-v8-holdout.json
```

This benchmark compares the deployed policy with ablations and simple
baselines. It is explicitly not an ARC score; see
[`VALIDATION_V8.md`](VALIDATION_V8.md) for the latest frozen claim boundary and
criteria, and [`VALIDATION_RESULTS.md`](VALIDATION_RESULTS.md) for the original
falsification plus the v2–v8 confirmation results. V3 supports narrow
conditional accommodation; v4 supports executable transformation composition
and v5 supports bounded possible/impossible reachability in control under
identical training histories. V6 supports direct causal transfer through a
typed finite comparison; v7 supports bounded endpoint-valid two-step
comparison composition; v8 supports explicit meta-evaluation and held-out
normalization by one bounded language-invention mechanism. None is evidence of
general equilibration, unrestricted category-theoretic cognition, arbitrary
language invention, or official-game generalization.

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

The Python package is organized by responsibility:

- `reflector/core/` is the deterministic symbolic inference engine.
- `reflector/runtime/` owns deployed policy execution and serializable traces.
- `reflector/research/` contains development-only evaluation and validation.
- `reflector/evolution/` contains candidate generation, persistence, and
  isolated selection.
- `reflector/cli.py`, `reflector/kaggle.py`, and `reflector/web_api.py` are
  composition roots. Legacy top-level module imports remain compatibility
  aliases; canonical internal imports follow the package boundaries above.

See [KAGGLE.md](KAGGLE.md), [ARCHITECTURE.md](ARCHITECTURE.md),
[THEORY.md](THEORY.md), [EVALUATION.md](EVALUATION.md), and
[PRIZE_READINESS.md](PRIZE_READINESS.md). Requirement-by-requirement status is
maintained in [COMPLETION_AUDIT.md](COMPLETION_AUDIT.md).

## Status

The end-to-end Kaggle baseline now includes online schemas, causal and temporal
hypotheses, explicit experiment questions, bounded event-goal planning, and
utility-gated synthetic concepts. It now derives bounded spatial relations,
MDL-positive schema families and concept types, and evidence-gated symbolic
language versions, including a compositional ℤ₄ orientation operator when
repeated rotation evidence pays its cost. Accepted concepts become later schema
terms, language operators normalize later events, and family confidence feeds
the bounded planner. The bounded language inducer is now itself a parented,
evidence-bearing symbolic object with falsifiable proposals, rejected trials,
retained products, a complexity charge, and a same-evidence ablation.
Evidence-backed translations now compile into explicit
operator objects used by a bounded spatial planner; the inference trace also
exposes represented inverses, finite modal reachability, and a typed comparison
graph with executable finite law checks. Context-typed operator systems can
now learn an evidence-backed square-symmetry comparison, infer a withheld
operator with provenance, reject inconsistent calibrations, and use the
inference in bounded planning. Perceived link tokens also support bounded
endpoint-valid chaining through an inferred intermediate operator while
preventing unrelated domains from becoming direct comparison shortcuts.
Development tooling measures recoverable
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
