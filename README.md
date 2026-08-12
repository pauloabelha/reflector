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

## Causal entity induction

R2 can now induce a bounded `CausalEntityBinding` when several visible regions
repeatedly undergo one coherent action-conditioned transformation while
preserving their relative layout. This closes the gap between atomic visual
segmentation and control: an induced assembly implements the same
`SpatialEntity` geometry interface as an atomic region, so ordinary potentials,
explanations, effects, and planners can consume its union geometry without
learning a second object representation.

Induction is deliberately defeasible. A candidate needs two independent,
environment-cited settlements before it becomes `SUPPORTED` and uniquely
role-eligible. Opposite or state-dependent effects under different opaque
actions do not destroy entity identity; a member breaking away from the shared
transformation does. Scene-wide motion is retained as a competing reference-
frame explanation instead of being promoted automatically. Support grants one
bounded role-grounding reservation, not preference, planner authority, or
permission to act.

The production lifecycle preserves the true predecessor regions and digest
until the action settles. This matters because Agent Arcade fits the successor
before controller settlement, whereas some headless callers settle first. Both
orders now compare the real before/after boundary, and a supported entity is
remapped to the fitted successor atoms and installed immediately. Its
action-conditioned translation or invariance is then available through the
ordinary effect model before the next rank/plan cycle. The browser publishes
the successor frame, settlement, and CAE audit atomically, so it never displays
a new frame beside an old settlement.

The inducer contains no game name, action token, direction name, member count,
color, or FIT-specific rule. `FIT` and `fit_residual` remain generic,
hand-authored ontology outside entity formation; they may consume a supported
assembly but do not cause one to exist. A six-transition held-out replay from a
live AR25 trace formed and supported two different coherent assemblies,
retained inverse action-conditioned effects, and refuted the larger assembly
when a member broke away. This verifies the mechanism, not improved control or
score.

Semantic settlement also separates two claims that were previously conflated:
an action effect may be confirmed even when the proposed goal potential never
improves. R2 retains the learned mechanism, counts uniquely grounded
nonprogress independently, and asks the semantic abductor to revise an
unsupported goal only after repeated observations. Just-settled counters are
projected immediately rather than through the pre-action ranking snapshot.
The rule contains no game, action, object, color, or verb-specific branch.

The current full suite has 240 passes and one unrelated failure caused by the
pre-existing missing historical experiment artifact
`parallel-cognitive-workspace-v1-16/artifacts/SUMMARY.json`. See the detailed
evidence boundary in [`R2_2.md`](R2_2.md).

A no-code-change CD82 transfer trace exercised this boundary live: a grounded
candidate's zero-progress count appeared immediately at 1, 2, and 3; Qwen
replaced the failed outline hypothesis with a distinct interior-compatible
alternative and ultimately retired the goal list when that alternative gained
no support. The level was not completed, so this is evidence of causal hygiene
and liveness, not competence or score.

The same long trace revealed that the semantic request duplicated its durable
working note across three transport fields and could overflow local Qwen's
context even at the mandatory graph closure. The request now contains one exact
model scratchpad plus a compact structured prior for validation. An exact CD82
rerun crossed the old turn-9 crash, completed Qwen call 10, settled action 10,
and began call 11. At that checkpoint, 240 full-suite tests passed plus the one
pre-existing missing historical score artifact failure.

Exploration also learns ordinary atomic mechanics before Qwen has a useful
goal. Effects enter the model only through mutual UNIQUE correspondence; an
ambiguous duplicate contributes nothing. When a later semantic proposal binds
to a prelearned effect, R2 first authorizes an identity-only probe and grants
progress/planner eligibility only after UNIQUE settlement. On predeclared
CN04, this learned rigid atomic effects before any active semantic explanation
while CAE independently retained a coherent three-member candidate. The full
suite now has 244 passes plus the same historical artifact failure; no CN04
completion or score improvement is claimed.

Same-transition evidence is pooled by intrinsic entity type before updating
the ordinary effect model. Agreeing instances add one observation with an
auditable `entity_count`; heterogeneous same-type outcomes add none because a
role or context factor is missing. On DC22 this reduced one settlement from 32
entity-level records to 14 type-level records while retaining multiplicities
11 and 8 and the real 2-cell translation. Current verification is 245
full-suite passes plus the same historical artifact failure; no DC22 completion
or score improvement is claimed.

Semantic revision is now an evidenced durable obligation. When a fresh
settlement carries explicit unsupported R2 semantic failure, Qwen cannot clear
the obligation by repeating the prior state or changing only one explanatory
phrase: a valid
response must revise `notes` and at least one of `explanation`, `goal`, or
`expectation`. The obligation survives rejected retries and failed-candidate
retirement, but is absent when no failure is evidenced. On DC22, calls 4 and 7
were denied fresh semantic status while grounded control continued. No DC22
completion or score improvement is claimed. Current verification is 246
full-suite passes plus the unchanged missing historical artifact failure.

When mutually unique same-type entities have different rigid outcomes in one
intervention, R2 now emits bounded `unresolved_effect_contexts` telemetry while
learning no type-level effect. The record preserves the distinct deltas and
their entity counts, explicitly without control authority. This supplies the
evidence needed to test future role/context factors without inventing them from
a single game or transition.

The committed read-only audit replayed this detector across 101 deduplicated
AR25, BP35, CD82, CN04, and DC22 transitions and found zero live context-demand
records. Accordingly, R2 has not induced a sequence, spatial, or role context
factor. The synthetic conflict is a safety test, not evidence that such a
factor exists in these games.

Explicit semantic failures use a focused repair transport. It keeps the exact
causal pair and R2 settlement, but does not make the semantic model regenerate
unrelated aliases, citations, or abductive diagrams. Previously compiled
evidence-cited aliases survive independently; goal proposals may be revised,
replaced, or omitted, and R2 still exclusively grounds and controls. On DC22,
focused prompts used about 44% fewer tokens, two insufficient repairs were
rejected, and the accepted revision acknowledged nonprogress while its repeated
goal proposal was retired. This is not a level-completion or score claim.

A failed semantic proposal now also loses action authority while its
evidence-based revision is pending. This is selective suspension, not
forgetting: the exact note remains visible to Qwen and Arcade, unrelated
proposals remain eligible, and independently learned action effects remain
available. A DC22 replay stopped controlling from the failed alignment
potential at three nonprogress observations instead of continuing through six
while repair retries were rejected.

Post-action semantic updates use a bounded generic instruction surface while
retaining the exact prior scratchpad, ordered predecessor/successor images,
strict response schema, and canonical compiler checks. This repaired a CD82
request that exceeded local Qwen's context by 500 tokens; the replay integrated
that update and the next one without removing causal visual evidence. These are
control-safety and transport-liveness results, not score or completion claims.

New measurable goals expose canonical binary formal ports (`actor,target`) to
the constrained generator. This replaces unreliable cross-field role arrays,
while the compiler remains backward-compatible with existing multi-role notes.
Visual categorical relations are generated only as defeasible clues, never
hard requirements. A ledger audit found 51 dependent-role failures across five
games before this change. Fresh CD82 then compiled consecutive goals without
those failures, and AR25 grounded a hole-based occupancy/negative-space
residual whose value decreased from 53 to 32 over six confirmed observations.
That is local potential progress, not yet a level or score terminal.

Semantic goal identity is independent of frame-local role-candidate identity.
Grounding candidates remain separate hypotheses, but once a selected candidate
settles into actor/target trajectories, overlap or occlusion cannot silently
reset its evidence counters. On exact AR25 replay, the repaired build retained
one goal key, both trajectories, and seven confirmations across the probe that
previously fragmented them, then recorded an eighth confirmation. The honest
tracked residual remained 30 rather than switching to an unrelated pair at 7.

Supported goals now distinguish lifetime evidence from controller-frontier
stagnation. R2 tracks the best observed potential for each semantic goal and
counts measured steps since that best improved; a recovery to an old best does
not reset the count. Four no-new-best steps request one focused complementary
abduction while preserving the proven goal, role trajectories, and mechanisms.
The compiler keeps the prior goal if the model abstains and may append only a
valid distinct refinement. An accepted repair acknowledges that exact
goal/frontier epoch, so ordinary semantic updates continue without repeatedly
raising the same plateau. Exact AR25 replay triggered one such repair at best
27 with eight confirmations and retained the original hole-based goal. This is
control-loop repair, not a level or score result.

Goal support is now settled from strict improvement of the measured semantic
potential, independently of whether R2 already predicted the action mechanism.
A novel useful intervention can therefore advance the goal frontier while its
entity displacement is learned as a new effect; mechanism confirmation updates
separate explanation evidence. Returning to an old best remains local progress
but supplies neither new goal support nor a frontier reset. Live AR25 recorded
a strict 38 → 35 frontier advance and separately confirmed the observed
three-cell mechanism. This is evidence separation, not a completion claim.

Semantic models can now project a novel relation or dynamic below the goal
layer through a bounded `schema_hypotheses` contract. Each hypothesis links to
one independently measurable goal, uses canonical spatial ports, declares
structural predictions and counterconditions, and enters R2 with zero support.
R2 recursively binds it to primitive or CAE entities and exact legal commands;
model confidence affects only attention tie-breaks. Environment settlement
then supports, refutes, or leaves the explanatory schema open independently of
entity identity, mechanism, goal-frontier, CAE, and environment-terminal
evidence. Fresh local Qwen used this channel without a concept-specific prompt,
and R2 correctly left its first contact/containment hypothesis open because the
observed command was not diagnostic. No semantic-quality, score, or transfer
improvement is inferred.

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
**PLANNER · GOAL PROSPECT** box and a separate **CAUSAL ENTITY INDUCTION** audit
box alongside goal proposals, abductive compositions, open questions, aliases,
citations, and the exact model scratchpad. Frame and settlement publication is
atomic, preventing transient mixed-boundary UI states; raw JSON remains
available for audit.

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
