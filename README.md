# Reflector II

Reflector II (R2) is a deterministic research agent for ARC-AGI-3. It combines
a sparse, content-addressed schema graph with a visual-semantic model, while
keeping grounding, action authority, evidence, and settlement inside R2.

The current production agent is **R2.2**, implemented under
[`src/reflector2/r2`](src/reflector2/r2). It is the model-neutral successor to
the R2.1 explanation-guided controller: the same runtime powers Agent Arcade
and Kaggle breadth runs, and it can use either the resident local Qwen service
or OpenAI models through `OPENAI_API_KEY`.

> Current evidence is still limited. R2 has repeatedly cleared AR25 level 1
> and has demonstrated grounded verbs, executable explanations, prediction
> settlement, and explanation consolidation. It has not demonstrated broad
> public-game competence, sealed transfer, or a competitive Kaggle score.

## Current architecture

```text
configured semantic model                         optional planning model
    proposes concepts, verb schemas,              proposes bounded command IDs
    abductive compositions, and working state               |
                         |                                  v
                         +------> R2 recursive workspace <---+
                                  validates and grounds
                                           |
                                           v
                            controller-neutral planner boundary
                       fallback-only | bounded search | model-validated
                                           |
                                           v
                            R2 authorizes exactly one command
                                           |
                                           v
                                    ARC environment
                           observes, scores, and settles
                                           |
                                           +---- evidence returns to R2
```

The authority boundary is model-independent:

- The model may propose bounded, action-free semantic structures.
- R2 alone binds visible entities, measures potentials, learns mechanisms,
  ranks actions, grants temporary control authority, and settles predictions.
- The environment alone supplies successor facts, score, support, and
  refutation.

Durable names such as `QwenTaskCompleted` remain compatibility identifiers in
the inherited event ledger; they do not imply that the active provider is
Qwen.

## Explanations, verbs, and goals

A Verb is a reusable schema over preferred change, not an ARC action. For
example, `FIT(actor, target)` may define progress as decreasing
`fit_residual = boundary_gap + overlap_deficit` toward zero.

An executable Explanation is a situated graph joining:

```text
grounded verb + bound roles + measurable potential
+ supported causal mechanism + predicted successor
```

R2 ranks actions through a hard epistemic gate:

```text
validated PLAN_ELIGIBLE > PROGRESS_ELIGIBLE
                        > discriminating PROBE_ELIGIBLE > INELIGIBLE
```

Every authorized action is observed and settled before the next one. Confirmed
explanations may enter a bounded fast path; contradiction revokes that
authority. Deep consolidation can derive reusable schemas at a level boundary,
but transferred schemas begin with zero empirical authority and must bind and
earn support again.

## Pluggable control factorization

Planning is a replaceable component, not part of R2's ontology. The independent
[`reflector2.planner`](src/reflector2/planner/README.md) package imports no R2
modules. R2 adapts grounded explanations and supported command-scoped effects
into a `ControlProblem`, injects any `PlannerBackend`, and remains the sole
owner of evidence, settlement, and external action authority.

Four backends implement the contract:

- `NoPlanPlanner` preserves the original one-step controller;
- `BoundedBestFirstPlanner` searches supported causal effects under explicit
  depth, frontier, expansion, confidence, and milestone budgets;
- `ProspectPlanner` derives bounded `GoalProspect` values from an R2-owned
  `GoalContract` and can justify a locally adverse first step only when an
  explicitly supported terminal-reaching factorization exists;
- `ModelPlanner` accepts either `QwenPlanningModel` or `LunaPlanningModel`
  through one structured model interface, then deterministically replays and
  validates every proposed edge.

A plan is a prospective causal factorization, never empirical evidence. Its
certificate can authorize only the first exact `ActionCommand`. The real
successor is then observed, the whole continuation is invalidated, and R2
replans. Only a settled positive edge may contribute fresh support to the
existing bounded fast path, with the route and certificate removed.

The matched AR25 experiment validates the modularity and safety semantics but
does not show a stronger controller: bounded deterministic planning matched the
original R2 action-for-action, while Qwen produced one causally matched but
worse divergence and was much slower. See the
[`AR25 planner results`](experiments/r2-2-planner-ar25-v0/RESULTS.md) and the
[`planner architecture note`](docs/R2_2_PLANNER_REPOSITORY_UNDERSTANDING.md).

R2.3 now implements the minimum structured `GoalContract` and derived
`GoalProspect` path as an experimental backend. Model proposals remain OPEN;
only cited environment settlements can support or refute a contract. Current
real-game evidence has not yet demonstrated a useful planner divergence or a
score gain, so R2.2 bounded search remains the production default. See
[`R2_1.md`](R2_1.md), [`R2_2.md`](R2_2.md), and the
[`R2.3 experiment`](experiments/r2-3-prospect-planner-v0/RESULTS.md).

## Shared semantic workspace

Each semantic response has two separate products:

- `model_scratchpad`: fluid, unverified semantic state shared by ordinary
  model turns, deep consolidation, and Agent Arcade.
- `workspace_write`: structured, cited proposals that R2 may compile and
  ground.

The scratchpad has exactly five nonempty string fields:

```json
{
  "game_objective": "current evidence-bound account of winning",
  "explanation": "current semantic explanation",
  "goal": "current action-free subgoal",
  "expectation": "falsifiable next expectation",
  "notes": "uncertainty, evidence, and revisions"
}
```

The canonical object is stored, passed back to the model without field
renaming, and rendered directly in Arcade. It is not evidence or control
authority. Structured `goal_proposals` and `abductive_compositions` from
`workspace_write` are the semantic inputs that enter R2 grounding and ranking.

The loop is settlement-synchronous: each environment transition requires a
semantic revision against the latest evidence before another external action.
A stale model response cannot overwrite newer workspace state.

## Requirements and installation

- Python 3.11 or newer
- `arc-agi==0.9.9`, installed from `pyproject.toml`
- `pytest` for tests

```bash
git clone git@github.com:pauloabelha/reflector.git
cd reflector
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

Important installed commands:

```text
reflector2-agent-arcade   current R2 agent and Arcade server
reflector2-r2-kaggle      current R2 Kaggle breadth runner
reflector2-arcade         human-controlled ARC interface
reflector2-workspace      frozen historical shared-workspace solver
reflector2-arc            offline ARC harness and older policies
reflector2-benchmark      deterministic schema-runtime benchmark
```

## Run Agent Arcade

### Local Qwen

The default profile uses the resident OpenAI-compatible Qwen service:

```bash
.venv/bin/python -m reflector2.r2 --arcade --game ar25 --port 8767
```

Open <http://127.0.0.1:8767/arcade>.

### GPT-5.6 Luna

Load the existing OpenAI key into the parent shell without copying it into this
repository:

```bash
set -a
source ~/inhambu/.env
set +a

.venv/bin/python -m reflector2.r2 --arcade --game ar25 --port 8767 \
  --model-profile openai-gpt-5.6 \
  --model gpt-5.6-luna
```

The browser picker intentionally offers only **Qwen (local)** and **GPT-5.6
Luna**, with server-owned safe defaults. The game, level, and model selectors
share the run-control row with a planner selector. Deterministic bounded search
is selected by default; **Goal prospect (R2.3)**, original one-step R2, and
model-validated planning with the selected Qwen/Luna model are explicit
alternatives. The full right-hand Workspace includes a dedicated
**PLANNER · GOAL PROSPECT** box alongside goal
proposals, abductive compositions, open questions, aliases, citations, and the
exact model scratchpad; raw JSON remains available for audit.

Arbitrary supported models and explicit budget experiments remain available
through the CLI and Kaggle runner. They are intentionally not exposed as a
large browser configuration surface.

## Model profiles and budgets

The known GPT-5.6 profile currently declares:

| Dimension | Default |
|---|---:|
| Context window | 1,050,000 tokens |
| Ordinary output | 8,192 tokens |
| Deep-consolidation output | 16,384 tokens |
| Dependency-closed R2 frontier | 12,000 tokens |
| Ordinary reasoning | medium |
| Consolidation reasoning | high |

OpenAI requests use the Responses API and its input-token counter. Admission
counts the exact canonical multimodal payload and JSON schema, then reserves
the configured output budget. Unknown model limits are never guessed:
`openai-custom` requires explicit context, ordinary-output,
consolidation-output, and frontier budgets.

The API key is read only from the configured environment variable at request
time. Requests, manifests, results, and telemetry record non-secret model and
budget metadata but never the credential. Transient failures receive bounded,
idempotent retries; permanent transport, schema, and compilation failures fail
closed without model authority.

Detailed configuration and examples are in
[`src/reflector2/r2/README.md`](src/reflector2/r2/README.md).

## Kaggle ARC-AGI-3 runs

Kaggle uses the same source closure, model transport, budgets, and
`run_game` implementation as Arcade:

```bash
set -a
source ~/inhambu/.env
set +a

.venv/bin/python -m reflector2.r2.kaggle \
  --global-seconds 27300 \
  --per-run-seconds 900 \
  --model-profile openai-gpt-5.6 \
  --model gpt-5.6-luna
```

The breadth manifest freezes the complete production
`src/reflector2/r2` closure before launching workers. Each result records the
resolved provider, model, budgets, reasoning settings, timeout, and retry
policy.

## Repository map

```text
src/reflector2/r2/   canonical R2.2 controller, workspace, model transport,
                    schema adapter, Arcade entrypoint, and Kaggle runner
src/reflector2/planner/
                    controller-neutral planner contracts, deterministic
                    search, plan certificates, and Qwen/Luna model adapters
arcade/              presentation, playback, and human-controller surfaces;
                    no agent policy or model backend
src/reflector2/      core sparse schema runtime and older evaluation tools
tests/r2/            canonical R2 runtime/model contracts
tests/arcade/        Agent Arcade presentation contracts
docs/                theory, language, architecture, invariants, and audits
environment_files/   bundled public ARC-AGI-3 environments
experiments/          isolated historical research code and evidence artifacts
reflector1-learnings/ archaeological sources; never imported by production R2
```

Production imports and manifests do not resolve through `arcade/` or
`experiments/`. R2 carries the frozen runtime ancestry it still requires under
`src/reflector2/r2/_runtime/`. Experiment directories remain evidence and
regression material, not the current agent implementation.

## Other interfaces

Start the human-controlled ARC interface:

```bash
.venv/bin/reflector2-arcade --environments-dir environment_files
```

It executes only browser-selected actions and is not an agent policy. See
[`arcade/README.md`](arcade/README.md).

Start the read-only perception inspector:

```bash
.venv/bin/python inspect/server.py --port 8765
```

Both interfaces bind to `127.0.0.1` by default.

## Documentation

- [`R2_1.md`](R2_1.md): R2.1 architecture, evidence, and explicit status
  boundaries.
- [`R2_2.md`](R2_2.md): current production migration and model-neutral
  transport.
- [`src/reflector2/r2/README.md`](src/reflector2/r2/README.md): operational
  model, budget, Arcade, and Kaggle guide.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): core runtime architecture.
- [`docs/THEORY.md`](docs/THEORY.md): operational epistemic vocabulary.
- [`docs/LANGUAGE.md`](docs/LANGUAGE.md): schema DSL and graph syntax.
- [`docs/INVARIANTS.md`](docs/INVARIANTS.md): executable representation and
  runtime constraints.
- [`SCORES.md`](SCORES.md): canonical result ledger and per-game matrices.

## Research and evidence convention

Implemented behavior, observed evidence, and prospective design must remain
distinct. A successful transport call, valid JSON response, deep schema graph,
or attractive explanation is not game competence. Promotion requires
executable contracts and, where competence is claimed, matched environment
evidence.

Each new experiment belongs under `experiments/<slug>/` with its initiating
context, preregistered method, configuration, code, result, and honest verdict.
Large traces should remain outside the production package.

The next central empirical test is a matched multi-game comparison holding R2
source, game order, action/time budgets, and profile constant while varying the
semantic model. Report score, actions to progress, compilation rate, semantic
pickup, explanation-lock churn, latency, token use, transport failures, and
cost—not model fluency alone.
