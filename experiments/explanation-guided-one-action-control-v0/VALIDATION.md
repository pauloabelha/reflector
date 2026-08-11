# R2.1 Arcade Validation

This file records the reliability contract and the latest manual smoke matrix.
It is evidence that the runtime executes; it is not evidence that R2.1 solves
every game.

## Automated contract

Run from the repository root:

```bash
.venv/bin/python -m pytest \
  experiments/explanation-guided-one-action-control-v0/test_contracts.py \
  experiments/parallel-generative-schema-fitting-v0/test_schema_engine.py \
  experiments/parallel-cognitive-workspace-v0/test_qwen_worker.py -q
```

The suite currently contains 68 passing tests. It covers:

- a fresh recursive workspace on every episode;
- three consecutive episodes with identical first frames;
- no cross-episode action-effect or prediction leakage;
- idempotent fitting after preferred completion becomes reified;
- repeated ranking and causal settlement;
- runtime reset delegation before environment execution;
- bounded Qwen transport on dense graphs;
- bounded read-only R2 explanation/verb/schema feedback on the next Qwen turn;
- controller publication after both ranking and empirical settlement;
- episode reset of semantic feedback and action traces;
- frame-zero current-only visual evidence;
- exact predecessor/current ordering and shared transition identity;
- rejection of reversed causal pairs and bounding to one older salient frame;
- binding the observed historical action and prediction settlement to the pair;
- bounded typed correspondence fitting across several recursive binding levels;
- sparse residual vectors without a built-in `Close` predicate;
- cross-frame residual-decrease bindings in the ordinary schema workspace;
- Qwen abductive composition restricted to R2-exposed stable schema IDs;
- R2 grounding of abductive diagrams and projection of open prediction shadows;
- rejection of stale component definitions before they can affect control;
- Qwen response, citation, scratchpad, and action-quarantine contracts;
- recursive schema-engine closure and Qwen-worker durability;
- required arcade surfaces and embedded JavaScript syntax.
- modal semantic clues with legacy clues defaulting to `suggested`;
- Pareto-bounded role hypotheses with exposed generic residual vectors;
- recovery from a deliberately incorrect suggested role clue;
- hard rejection of the same clue when explicitly `required`;
- translation, value-swap, scaling, T/Z/irregular-shape, and distractor
  invariance for the generic role grounder.
- frozen predecessor snapshots when the successor workspace is fitted before
  settlement;
- selection of the best retained comparative hypothesis for an
  unknown-mechanism probe;
- strict mutual-occlusion identity fitting, rejection on unexplained exposed
  pixels, and installation of the latent whole-role factorization for the next
  decision.

Python compilation, embedded JavaScript `node --check`, and `git diff --check`
must also pass.

## Live categorical-abduction proof — 2026-08-10

Three fresh AR25 arcade runs were used while hardening the new path. The first
exposed an oversized semantic contract: Qwen emitted two diagrams plus three
verbs, reached the 1,280-token generation boundary, and left an unterminated
JSON string. The contract now admits exactly one diagram per semantic round,
with 2–3 component schemas, 1–3 morphisms, at most two residual projections,
and at most two verb proposals. The next run produced a valid compact diagram.
It also exposed that later Qwen notes were displayed from `scratchpad` while
the controller continued reading the frame-zero `current_explanation`; the
controller now consumes the latest accepted scratchpad note first.

The final fresh run demonstrated the complete loop without a runtime or schema
error:

- frame 0 fitted 11 regions and recursive bindings before any action;
- the first Semantic Qwen write was accepted before action 1;
- later categorical passes stayed at the configured 64-correspondence and
  64-temporal-comparison bounds while comparing 18 binding types, including
  regions, relations, verbs, causal effects, potentials, explanations, and the
  newly grounded abductive composition itself;
- Semantic Qwen proposed one `constrains` diagram over two stable schema IDs;
- R2 grounded it as stable schema `schema:d53d18ca34103b5e` in four situated
  assignments and projected one open prediction shadow from each;
- every grounded result was labeled
  `grounded-structural-open-prediction`; none was rejected;
- the episode reached turn 16 while the next semantic update ran in parallel.

This is evidence of structural grounding, not evidence that the proposed
`outline_disagreement` residual is already a generally useful winning
abstraction. Its shadow remains open until later observations support or
refute it.

## Live semantic-feedback proof — 2026-08-10

An AR25 run was allowed to reach three Semantic Qwen turns. The durable turn
artifacts showed the expected episode sequence:

- frame-zero turn: no R2 feedback, because no action had yet been ranked;
- revision 3480: `r2.1-semantic-projection-v1` present;
- revision 6667: a later, updated projection present.

The later request contained an `active-progress-explanation` for `fit`, a
`fit_residual` potential, 16 salient structural bindings, 12 open shadows, the
latest settlement, and the explicit authorities `r2-only` for action selection
and `qwen-proposal-only` for semantic revision. The compact inference request
contained the same projection and was accepted by the local Qwen server. The
arcade's scratchpad column now renders a concise summary of exactly this
feedback under “R2 FEEDBACK · READ BY NEXT SEMANTIC QWEN”.

## Live smoke matrix — 2026-08-10

Each ordinary pass used the public arcade API, started from level 1, accepted a
frame-zero Qwen workspace write before acting, and checked both runtime error
and R2.1 schema telemetry error.

| Game | Actions observed | Qwen note | Grounded verb | Runtime/schema error |
|---|---:|---|---|---|
| `ar25` | 3 | accepted | `fit` | none |
| `cd82` | 3 | accepted | `fit` | none |
| `cn04` | 3 | accepted | none; information fallback | none |
| `dc22` | 1 within the smoke window | accepted | `fit` | none |

`bp35` was also used as a dense-graph stress test. Before the transport fix,
its first request was 41,418 tokens and the 24,576-token local Qwen server
rejected it. After the fix, the serialized inference request fell from about
82 KB to 35 KB, Qwen completed, the note was accepted, R2 grounded `fit`, and
the run reached action selection without an error. BP35's dense frame remains
too slow after grounding to count as a completed action-settlement smoke pass.

## Live causal-frame proof — 2026-08-10

An AR25 post-action request at turn 16 was inspected from its durable inference
artifact. Its visual sequence began with exactly:

```text
CAUSAL_UNIT_PREVIOUS_FRAME order=1/2 ... transition_ref=vt:75a9c3da9f86486f
CAUSAL_UNIT_CURRENT_FRAME  order=2/2 ... transition_ref=vt:75a9c3da9f86486f
```

The request contained exactly two primary images and the two labels shared the
same transition identity. Its structured `r2_transition_observation` identified
historical action 3, marked the observation as changed, included R2's grounded
object-motion trace and learned effects, carried the prediction adjudication,
and labeled its role `observed-history-not-action-proposal`. The same structure
was present in the actual Qwen prompt text.

## Failure fixed

The reported `StopIteration` was caused by two coupled assumptions:

1. an identical frame digest could reuse the previous episode's schema
   workspace;
2. preferred-completion fitting was assumed always to return a partial binding.

New episodes now reset all epistemic state before `run_episode`. Open-binding
construction accepts partial or already-reified candidates, and causal-chain
materialization safely reuses an existing completion atom. These are separate
guards: episode isolation prevents evidence leakage, while idempotency prevents
valid completed structure from becoming an exception.
