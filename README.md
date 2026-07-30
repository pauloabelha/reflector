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

Last verified: 2026-07-29

> **Plain-language result:** Reflector has fully beaten **0 of 25 games**.
> It has solved **19 of 183 levels across 10 games**. All 25 games were
> evaluated; “25/25 evaluated” does not mean “25/25 beaten.”

| Metric | Accepted v49b result |
| --- | ---: |
| Complete games beaten | **0 / 25** |
| Games with at least one solved level | **10 / 25** |
| Levels solved | **19 / 183** |
| Official local score | **4.6401724704 / 100** |
| Games evaluated | **25 / 25** |
| Kaggle submissions | **0** |

The score is about **4.64% of the 100-point scale**. It is a local
public-development result, not a Kaggle leaderboard score. V49b preserves all
18 accepted v47b levels exactly and adds `m0r0` level 1 in 20 actions. It
grounds a reflected congruent object pair, learns the joint displacement
caused by each plain action, plans over an independently blocked substrate
topology, and permits at most two evidenced continuation actions when contact
temporarily merges the pair. Two target runs and two ten-game preservation
gates were exact. The full suite runs every game in a fresh process. The exact
package passes 209 tests (3 skipped), Ruff, mypy, both offline smoke paths, and
export. No hidden Kaggle score exists.

A new paired pure-symbolic control makes the local gain more interpretable.
Under the same 25 games and 10,000 actions, a deterministic connected-object
and frame-graph frontier explorer scored **0.0003283918/100** and solved
**1/183 levels**, versus v40's **4.2992976365/100** and **16/183**. The control
created 5,130 distinct frame states and 9,185 changing transition targets,
showing that lightly normalized visual graphs are overwhelmed by nuisance
dynamics and hidden phase. This is a public-development comparison, not hidden
generalization evidence. The method, protocol, and full result are in
[the symbolic comparison](references/SYMBOLIC_ARC3_COMPARISON.md).

The subsequent v38 experiment is rejected and does not change these scores.
It inferred and executed a 17-action `sb26` level-4 program based on relocating
an aligned child marker, but the two relocation clicks produced no rendered
change and the level did not advance. Two frozen runs matched the source-matched
v37 control at `[9, 15, 15, 361]`. This negative result is retained because it
shows that visual alignment and attribute matching cannot substitute for
intervention evidence that an object is actually movable.

Two later probes also leave the accepted score unchanged. A research-only
local Gemma 4 E2B hybrid returned valid structured choices on all 40 `g50t`
actions but solved no level; its prose hypotheses remained generic, omitted
the commit action entirely, and sometimes contradicted the selected action.
It is neither purely symbolic nor Kaggle-compatible and was rejected. The
symbolic v41 committed-trajectory branch did learn action effects, a latent
macro, autonomous replay, and up to 21 contextual collision edges across
retries. After seven trace-driven variants it still solved 0/7 `g50t` levels
at 400 actions, so its preregistered 30-action target was falsified. These
negative results motivated v42's substrate topology and uncertain-gate
information actions. The accepted v49b result and all rejected predecessors are
documented in the [real-games scorecard](REAL_GAMES_REPORT.md).

A second hybrid tests the stronger architecture: the symbolic agent remains
the controller and Gemma is an internal arbitrator only after repeated,
explicit trajectory-gate failures. The action Gemma actually selects receives
the next transition's symbolic credit. On an 80-action `g50t` comparison it
matched the v43f symbolic control exactly at **1/7 levels and `[27, 53]`**.
Gemma was consulted 27 times, accepted 22 symbolic proposals, made five
overrides, and produced six invalid responses that safely fell back. It added
no level and still sometimes named a different action in prose than its chosen
candidate denoted. The hybrid is therefore rejected; it is not part of the
accepted v49b runtime.

The v26 research branch now preregisters intervention hypotheses, keeps
predictive and pragmatic credit separate, and treats successful action-role
programs as first-class inputs to bounded prefix, suffix, interleaving, and
role-binding variations. This machinery runs inside the offline agent and
never calls an LLM. It is not promoted: its only full-suite score increase
(2.9104325118 to 2.9202784571, with the same eight levels) came from
coordinate-free replay, while causal credit and scheme variation were neutral.
Two trace-driven accommodations reduced stale composite/replay actions as
predicted but did not improve task outcome. See the canonical report for the
falsifying comparisons.

The v28 object-perception branch adds content-free persistent-component,
composite-region, enclosure, normalized-shape, frame-difference, and
discrete-flow primitives with typed provenance. It remains experimental.
Primitive-guided intervention improved `ft09` and helped discover levels in
`lp85` and `sp80`, but the full offspring lost `tn36` and slowed `lf52` and
`r11l`; it was rejected. V40 inherits v31's causally earned graph-cycle policy,
v32's independently gated attribute-binding composition, v35's bounded nested
traversal, v37's enclosure-grounded sibling accommodation, and the independently
controlled shape-goal translation from v39. It adds only relational
phase-conditioned action semantics after its own target, preservation, and
full-suite controls. Other richer ontology traits stay behind exact-off genome
flags for future source-matched offspring.

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
V25 reaches five `ft09` levels and passes the source-matched non-regression
gate. Kaggle compatibility is proven locally; broad full-suite generalization
and competitive hidden performance are not.

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
