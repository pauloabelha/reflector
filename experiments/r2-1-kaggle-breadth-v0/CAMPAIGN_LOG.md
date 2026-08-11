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

## Checkpoint 5 — ordered observation envelope before the next freeze

Perception-evidence candidate:

- Toolkit observations now retain every frame support in supplied order under
  `ordered-observation-envelope-v1`, with per-support and packet digests.
- The last supplied support is explicitly marked as settled and remains the
  only frame consumed by existing R2.1 fitting and control, so this change does
  not infer animation semantics or alter action choice.
- Initial and successor observation blobs preserve the envelope beside the
  legacy settled `grid`; replay surfaces expose `ordered_frames` for the
  campaign's existing animation-evidence classifier.
- Live runtime state likewise retains the packet while publishing the settled
  frame to the existing UI/control field.

Verification before freeze:

- Multi-frame fixtures prove exact normalized order, order-sensitive packet
  identity, single-grid compatibility, final settled selection, live-runtime
  retention, inherited-ledger retention, and replay exposure.
- 194 repository, R2.1, command, envelope, and analyzer tests pass after the
  implementation; focused envelope/analyzer contracts also pass independently.

Status: contract-verified observability candidate. No claim is made that R2.1
interprets transient supports yet; a fresh real trace must first demonstrate
that the toolkit supplies multi-support packets for the selected games.

Real prevalence and provenance audit:

- Across 50 toolkit recordings and 12,025 observations, 2,763 packets (22.98%)
  have multiple supports; 2,002 contain more than one distinct support.
- Fourteen games contain multi-support observations. Recorded packets range
  from 2 to 42 supports.
- In the current frozen G50T trace, 7 of the first 13 observations are
  multi-support, including packets with 7–21 supports. Each envelope's declared
  settled support exactly equals the legacy control grid, while replay exposes
  the complete ordered packet.
- The failure classifier changes only `perception_animation_evidence` from
  static/partial to ordered evidence observed; all other layer assessments are
  unchanged.

Status: promoted as an observation/provenance repair. Interpreting transient
supports remains a separate unimplemented hypothesis.

Timeout accounting correction:

- The first frozen `g50t` deadline row reported null actions even though its
  ledger held 41 committed successors and one interrupted pending action.
- Future timeout/error rows recover actions and level clears only from durable
  `TransitionCommitted` events and report unresolved pending count separately.
- Malformed or half-written tail events are ignored rather than counted.

This correction changes campaign measurement only; it cannot manufacture an
environment action or level clear.

Live mixed/click regression and repair:

- `lf52` crossed five changing successors, including an exact grounded click;
  parallel click-only `lp85` reached planning as well.
- Both then exposed the same generic publication defect: an explicitly null
  optional `control_proposal` was treated as a mapping when checking fast-path
  mode.
- The controller now normalizes only that optional field to an empty mapping.
  A contract reproduces the null ranking and verifies ordinary probe selection
  remains unchanged.

Exact grounding-efficiency candidate:

- The audited FT09 frame contains 64 regions and 4,032 ordered role pairs, but
  only 29 distinct vectors in the exact dimensions used by Pareto dominance.
- The new index still evaluates every role pair, compares one representative
  per exactly equal vector, then restores every member of each nondominated
  vector before the unchanged ranking and top-k stages.
- Indexed and exhaustive grounding outputs are exactly equal on the real FT09
  frame: candidate count 4,032, Pareto count 994, and identical selected
  bindings. Measured grounding time fell by roughly 5.1–5.6×.

Frozen breadth restart:

- Revision `4b2932d` is pushed and preregistered in
  `run-20260811T041300Z-frozen-4b2932d` across all 25 local games.
- The invalid pre-fix campaign was stopped while AR25 still held the old
  controller in memory; its earlier G50T/LF52 traces remain diagnostic only.

Demand-driven Qwen audit:

- Of 61 durable queues in the audited breadth snapshot, 54 had observable
  demand (initial semantics, new unaliased-action evidence, or overlap with
  explicit refutation) and seven were positive-count cadence only.
- The cadence-only calls were 11.5% of queues; three were proven semantic
  no-ops, while none carried a causal-revision packet.
- Alias retries cannot be suppressed wholesale: later retries sometimes
  compiled successfully after earlier format rejection, and no duplicate exact
  `(workspace, action, evidence)` queue key was observed.
- Safe implementation requires replacing cadence with the exact causal-packet
  eligibility predicate plus initial, alias-evidence, and explicit unsupported
  semantic-failure demand. It remains designed, not yet promoted.

Parameterized repetition telemetry correction:

- Analyzer no-change identity now uses exact `selected_command.command_id` when
  present. Different click coordinates are distinct interventions even though
  they share `ACTION6`; simple actions retain action-ID identity.

## Checkpoint 6 — scored GAME_OVER retry boundary

Engine audit:

- RESET is not advertised in any of the 25 game action spaces, but direct
  post-action GAME_OVER audit states recover through engine action 0 in 25/25.
- Every audited successor was playable, `full_reset=false`, and retained the
  completed-level count. RESET is counted by the engine as an action/reset.

Implementation candidate:

- Only GAME_OVER may retry; WIN never resets. A retry is allowed only when one
  slot remains in the same current-level committed-action budget.
- Action 0 follows the exact durable pending/commit/replay chain with explicit
  `game-over-retry-reset` boundary provenance and arbiter authority.
- The successor fails closed unless it is playable, not a full reset, and
  preserves completed levels.
- Retry re-grounds situated state and clears pending prediction, bindings,
  plans, no-change exclusions and fast path, while retaining game mechanics,
  action-use evidence, recursive graph, and durable semantic note.
- Action 0 bypasses ordinary controller/cognition effects and cross-board graph
  correspondence, so RESET cannot become a learned motion mechanism.

Verification before freeze:

- Full selected suite passes, including budget/WIN gates, marker conflicts,
  successor invariants, retry-only cognition hooks, and exact checkpoint replay.

Status: contract-verified candidate; requires frozen real GAME_OVER evidence
before promotion as a score-preserving control improvement.

Parallel frozen LP85 diagnostic (`4b2932d`, ten-minute cap):

- 24 exact click successors committed; 3 changed the frame and 21 did not.
- No exact command/state no-change repetition and no decision/execution
  mismatch occurred. Different click coordinates were correctly treated as
  distinct interventions.
- Identity recorded BROKEN evidence, mechanics remained UNKNOWN, only five
  decisions were probe-eligible, and none was progress-eligible.
- No level cleared. This is evidence that transport coverage alone is
  insufficient: situated identity/mechanism grounding and selective click
  exploration now dominate this trace.

Late-run throughput audit:

- Frozen G50T action time rose from 9.34s/action in the early third to 40.15s
  in the late third; LP85 rose from 11.32s to 29.78s.
- Selected role-candidate counts stabilized early, while graph revisions and
  accumulated R2 bindings continued growing. G50T ended with 17,281 objects
  (11,636 R2 bindings); LP85 reached 20,853 (17,345 bindings).
- The non-Qwen residual rose from 0.96s to 27.50s/action on G50T and from 3.75s
  to 24.65s on LP85. Artifact timing localizes the bottleneck only to the
  cumulative schema/graph/ledger family, not yet to one function.
- The current G50T worker committed 34 actions in 900s, recorded 34 native
  predictions and five environment edges, and cleared no level.

Parallel transport caveat:

- G50T and LP85 shared one Qwen endpoint. Current G50T had 12 HTTP/JSON errors
  in 15 completed calls, versus 0/12 in the prior serial G50T trace.
- Parallel game workers are therefore not comparable score evidence and are
  discontinued on the shared endpoint. Implementation, testing, and read-only
  analysis remain parallel; scored workers remain serial unless model capacity
  is isolated.

## Checkpoint 7 — demand-triggered semantic scheduling

Intervention candidate:

- Positive action-count cadence no longer schedules Qwen.
- A call is due only while initial semantics lack a canonical valid note, when
  the exact v1.12 causal-packet predicate has an eligible unit, when new
  unaliased-action evidence exists, or after explicit unsupported R2 semantic
  rejection/refutation.
- The scheduler reuses the causal packet builder's canonical eligibility
  function. A malformed eligible unit remains due and raises the normal packet
  error rather than disappearing behind an approximate predicate.
- A rejected first compilation remains due until a valid note exists.
- Overlapping reasons feed one boolean queue gate; existing pending, replay,
  and maximum-call invariants are unchanged.

Verification before freeze:

- Leaf, v1.4, v1.12, campaign and selected repository suites pass in isolated
  processes, including initial reject→valid, exact causal eligibility,
  malformed packet, alias, overlap, and positive-cadence tests.

Falsified cap variant:

- An intermediate build enforced the previously inert global
  two-consecutive-failure config. In clean G50T it cut calls 50% by action 19,
  but the two failures belonged to different alias demands and the cap then
  suppressed later evidence-driven retries that succeeded in the prior trace.
- That cap is reverted. New durable alias evidence remains a valid demand after
  earlier compilation failures. Suppression requires a same-demand identity,
  which the current queue protocol does not yet persist explicitly.

Status: revised contract-verified candidate; requires a clean serial breadth
cohort to measure cadence savings without semantic starvation.

## Promotion discipline

A campaign intervention is promoted only after:

1. its intended dataflow is visible in provenance;
2. a targeted contract or same-state comparison supports its causal effect;
3. a later frozen, mechanic-diverse run checks transfer and runtime regressions.
