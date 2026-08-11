# R2.1 Kaggle breadth campaign log

This is the durable checkpoint journal for the adaptive eight-hour campaign.
It distinguishes observed evidence from inference and records the exact build
that produced each episode. Public-game results are development evidence, not
sealed transfer or Kaggle competence.

## Checkpoint 0 — baseline frozen before experimentation

- Baseline commit: `6617c64` (`origin/epistemic`).
- Contract suite: 65 passing tests at the initial checkpoint.
- Scope: R2.1 recursive schema/control implementation plus a deadline-bounded,
  modality-interleaved 25-game campaign runner.
- Authority boundary retained: Qwen proposes semantic schemas; R2 grounds,
  predicts, and ranks; only environment successors supply empirical support.

## Checkpoint 1 — headless experiment did not execute R2.1

Observed in aborted `run-20260811T032623Z`, game `g50t`:

- Qwen produced two accepted `fit`/`align` goal proposals.
- Every decision had `r2_1_explanation_control: null`.
- Actions followed the inherited information-cycle policy rather than R2.1.

Cause:

- `run_game(..., runtime=None)` installed no `LiveRuntime` and therefore no
  `FrameSchemaObserver`. Arcade runs supplied one explicitly, hiding the
  headless-path defect.

Intervention:

- Added `active_runtime()` so arcade and headless modes share the same R2.1
  observer substrate.
- Added a contract proving a caller-supplied runtime is preserved and a
  headless runtime receives a `FrameSchemaObserver`.
- Commit: `5462d0e` (`origin/epistemic`).
- Verification: 66 passing contracts.

Status: the aborted trace is invalid as an R2.1 capability result.

## Checkpoint 2 — R2.1 is active; generic probe/telemetry defects isolated

Observed in `run-20260811T032919Z`, initial `g50t` episode on build `5462d0e`:

- The first decision contains a grounded `fit` explanation and an R2.1
  `PROBE_ELIGIBLE` proposal.
- By the third executed transition R2 had learned a supported action effect and
  ranked action 2 as `PROGRESS_ELIGIBLE` with predicted residual improvement.
- This verifies that headless R2.1 dataflow now reaches control.

Prior arcade evidence:

- In `run-1786413577717702079`, AR25 level 2 repeated action 7 on the identical
  state five times while risk rose from 0 to 4; the proposal remained
  `PROBE_ELIGIBLE`.
- 102/1,802 stored arcade decisions had an R2-marked selected top action that
  differed from the decision contract's actually executed fallback.

Inference:

- An observed no-change for the same action at the same predecessor closes
  that exact probe. Repeating it without a changed hypothesis spends score but
  adds no visible discrimination.
- Unauthorized R2 rankings are useful advice but must not be represented as
  the executed selection.

Intervention:

- Same-state no-change now makes that action's progress/probe candidate
  ineligible until the state changes; after all alternatives are exhausted the
  broader fallback may still revisit latent-state hypotheses.
- Unauthorized rankings are retained under `advisory_top_actions`; executable
  `top_actions`, the decision, and the contract now agree.
- Commit: `5a42f76` (`origin/epistemic`).
- Verification: 68 passing contracts.

## Open high-priority findings

These are audited gaps, not implemented capability claims:

1. Complex/click actions occur in 19/25 local games and are filtered from the
   inherited simple-action path. Six games are click-only and therefore cannot
   currently be played by this controller.
2. Ordered animation frame stacks are collapsed to their final frame, losing
   transient evidence.
3. `GAME_OVER` currently terminates an episode instead of treating RESET as a
   costly retry intervention where competition semantics permit it.
4. Cross-level mechanic retention is exact-keyed and often requires full
   rediscovery after palette/scale changes. Any backoff must be structural,
   conservative, and probe-only until confirmed in the new level.
5. Result aggregation undercounts first-class R2 predictions and confirmations;
   control telemetry must not confuse absence from the inherited PCW counters
   with absence of R2 mechanism evidence.

## Checkpoint 3 — native R2 predictions enter the evidence graph

Observed in the still-running `g50t` episode from `run-20260811T032919Z`:

- At action 40 the workspace contained 40 action proposals, 121 control
  explanations, and grounded R2 predictions in the decision contracts.
- The inherited aggregate nevertheless reported zero durable prediction
  objects and zero support edges.
- Seven semantic turns repeatedly returned the same `fit` and `align` goal
  schemas while control evidence accumulated. This is recorded as semantic
  stagnation, not yet as a causal explanation for the failed clear.

Cause of the telemetry discrepancy:

- Native R2.1 predictions lived in `current_explanation.prediction`, while the
  inherited result builder counts only graph `prediction` objects and
  environment `supports`/`refutes` edges.
- R2.1 deliberately replaces the inherited plan with a fallback plan, whose
  inherited prediction list is empty.

Intervention:

- The selected, eligible, action-matching R2.1 prediction is now materialized
  before `ActionPending` with deterministic plan identity.
- Its immediately following confirmed/refuted settlement is merged into the
  existing prospective adjudication path, preserving inherited judgments and
  result hashing.
- The campaign summary now retains `prospective_chain`.
- Verification: 68 passing contracts, including exact one-shot settlement
  bridging and pending-identity clearing.

This patch changes evidence accounting, not the controller's action choice.

Boundary audit immediately after promotion:

- Fresh `lf52`, `ls20`, and `ar25` workers rejected the first post-action
  semantic projection because the native prediction depended on a quarantined
  control explanation whose open question named an opaque numbered action.
- The parent batch was stopped; these outcomes are invalid capability results.
- Correction: native prediction ancestry now points only to the latest frame,
  matching the semantic-safe boundary of inherited predictions. The proposal
  and environment settlement still retain exact control ancestry outside the
  Qwen projection.
- A fresh bounded `ar25` smoke then crossed two action/observation boundaries
  without the rejection and durably recorded two prediction objects. The
  smoke was intentionally killed at its two-minute cap, not scored as a
  completed episode.

## Checkpoint 4 — combined coverage build before freeze

Execution candidate:

- Added typed `ActionCommand` identity for simple and parameterized actions.
- Coordinate candidates are actual observed region cells nearest the region
  center (`x=column`, `y=row`), bounded and transport-validated.
- Exact payload now flows through decision, pending ledger, environment step,
  transition, replay, and intervention identity.
- No-change and learned effects are scoped to the exact command; one dead
  coordinate cannot suppress every click.
- Parameterized counterfactual branches are explicitly skipped until both
  branch payloads can be grounded, rather than executing invalid empty data.
- Click fitting is restricted to role diagrams containing the grounded clicked
  region, avoiding unrelated causal attribution and combinatorial work.

Semantic-efficiency candidate:

- Exact goal-set repetition is challenged only after explicit R2 grounding
  rejection or unsupported prediction refutation.
- Scheduler-only calls, open mechanisms/shadows, confirmed models, and
  progress-eligible explanations preserve a stable proposal.
- This guard routes failure evidence but never invents, ranks, or repairs a
  semantic goal.

Telemetry ordering correction:

- The first native prediction bridge left the inherited action proposal's
  selected-prediction list empty, so v1.9 correctly filtered later judgments
  as potentially post-hoc.
- A minimal native proposal now explicitly selects the already-durable native
  prediction.
- In a fresh nine-action `ar25` smoke, the graph recorded five environment
  support edges and one refutation edge.

Verification before freeze:

- 178 repository, R2.1, command, and analyzer tests pass.
- Failure-layer analysis distinguishes execution, perception/animation,
  identity, mechanics, telos/repetition, exploration, planning, runtime, and
  success while retaining explicit unknowns.

Real execution boundary:

- A fresh `ft09` smoke, which previously stopped at action zero because its
  only usable mechanic is parameterized, selected `ACTION6` with grounded
  payload `{x: 6, y: 4}`.
- `ActionPending` and `TransitionCommitted` contain the identical payload and
  command identity; the before/after frame digests differ.
- This proves transport coverage and exact provenance, not that the chosen
  click advances the level or that click planning is competent.

Status: promoted as an execution-coverage candidate. Breadth score and runtime
effects remain unverified; the next frozen campaign must test those separately.

Timeout accounting correction:

- The first frozen `g50t` deadline row reported null actions even though its
  ledger held 41 committed successors and one interrupted pending action.
- Future timeout/error rows recover actions and level clears only from durable
  `TransitionCommitted` events and report unresolved pending count separately.
- Malformed or half-written tail events are ignored rather than counted.

This correction changes campaign measurement only; it cannot manufacture an
environment action or level clear.

## Promotion discipline

A campaign intervention is promoted only after:

1. its intended dataflow is visible in provenance;
2. a targeted contract or same-state comparison supports its causal effect;
3. a later frozen, mechanic-diverse run checks transfer and runtime regressions.
