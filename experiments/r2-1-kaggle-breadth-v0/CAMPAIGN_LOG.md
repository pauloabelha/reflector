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

## Checkpoint 8 — corrected final serial cohort

- Pushed revision: `8beebf8`.
- Run root: `artifacts/run-20260811-final-serial-8beebf8`.
- Transitive frozen-source digest:
  `3f3e73dc9a4c87eaa6d862bc6b6b1d9e3097c21728192b6a82d7e75ff82b0a03`.
- Preregistered order: all 25 local games, modality-interleaved, one scored
  worker at a time on the shared Qwen endpoint.
- Remaining global allocation: 23,950 seconds with a 900-second finalization
  reserve and 900-second per-game deadline.
- Source drift before any later worker stops and finalizes the cohort rather
  than mixing controller builds.

This is the first cohort combining grounded parameterized actions, ordered
sensory envelopes, exact Pareto indexing, truthful native prediction edges,
GAME_OVER retry semantics, exact intervention analysis, and demand-triggered
semantic scheduling without the falsified global failure cap.

Corrected scheduler live audit through G50T action 22:

- Eleven queues: initial, nine unique alias-evidence demands, and one explicit
  refutation overlapping alias evidence. No cadence-only call occurred at
  action 8 or 20, and no evidence key repeated.
- Fresh evidence demands remained eligible after prior failures, validating
  the global-cap rollback.
- The seven restored post-cap calls produced no accepted write because every
  request exhausted model context, not because the scheduler was noisy.
- HTTP 400 responses report 16,779–17,658 prompt tokens against `n_ctx=16,384`.
  JSON decode failures end at exactly 16,384 total tokens with truncated or
  empty JSON. The request builder is not preserving its declared response
  reserve once system prompt/schema overhead is included.

Status: semantic scheduling promoted as causally clean; request budgeting is
the new blocking interface defect and is being repaired in an isolated
worktree.

## Checkpoint 9 — exact batched graph reduction and replay

Observed hot path:

- Each Qwen queue reduced the complete graph three times: controller refresh,
  orientation read, and Qwen history validation. At the frozen endpoints this
  cost approximately 53.5s on G50T and 83.2s on LP85 before model transport.
- Workspace ingestion also applied and re-sorted 393–827 `ObjectAdded` events
  one at a time although the outer ledger already persisted them atomically.

Intervention:

- Contiguous `ObjectAdded` runs validate sequentially against an evolving
  prefix, then perform one canonical final object/pickup sort. Edge and
  attention events remain on the original sequential path.
- Live R2 workspace ingestion stages its unchanged semantic order and commits
  the byte-identical returned graph events in the same outer batch.

Exactness evidence:

- All 16,694 G50T and 20,507 LP85 workspace object events regenerated
  event-for-event exactly. Every stored batch prefix, final state, object order,
  pickup, revision/head, state hash, and Qwen turn matches the sequential
  reducer.
- Randomized valid and corrupt traces match full state or exact exception
  class/message at every prefix.
- G50T full replay improved 14.86s→0.254s (58.4×), LP85
  22.97s→0.266s (86.3×); exact `build_turn` improved 37.9×/32.8×.
- Actual-scale live ingestion improved 47.8× in the isolated benchmark.

Status: pushed in `762f28d`; requires live cross-game throughput evidence.

## Checkpoint 10 — exact request admission

Reproduced defect:

- Four stored evidence-driven requests exceeded the 16,384-token model context
  or left too little space to complete valid JSON, despite a declared 2,048-token
  response reserve.

Intervention:

- Admission now tokenizes the complete serialized request with the same local
  GGUF tokenizer, conservatively accounts for images and template overhead, and
  preserves at least 2,048 tokens for the response.
- When necessary it performs one overflow-guided rebuild that reduces only the
  explicitly lossy ordered history frontier. Current transition evidence, live
  bindings, pinned causal units, and causal packets remain mandatory. If those
  cannot fit, the request fails locally before queue or transport.

Exact stored differential:

- The four former failures now occupy 16,265, 15,737, 16,099, and 15,551 tokens
  including the completion reserve. Each required exactly one rebuild.
- Mandatory bindings, causal packets, pinned units, and exact transition
  evidence references are unchanged.
- Integrated controller/graph/retry suite, full v1.4 suite, v1.12 suite, and
  stored regression all pass after combination with batched graph replay.

Portability boundary: the current configuration names this host's exact
`llama-tokenize` executable and GGUF. Missing paths fail closed and must be
reconfigured on another installation.

Status: pushed candidate in `942122e`; next frozen serial breadth cohort will
test real transport success, latency, and cross-game behavior.

## Checkpoint 11 — live admission boundary and staircase repair

Two failed launches are quarantined rather than scored:

- `final-serial-a16c455` ran inside a network-restricted sandbox. Three games
  stopped at frame zero with `Operation not permitted`; the first-frame gate
  correctly spent no action. This is infrastructure evidence only.
- `final-live-a16c455` reached the local model. G50T's initial semantics call
  transported and compiled in 13.7s, action 1 committed, then the action-1
  evidence revision failed locally at context admission by 19 tokens.

Root cause:

- Retry budgets 6,400→6,385→6,370 all rendered the same 3,655-token sparse
  cut. Nominal budget decrement treated the dependency-closed frontier as a
  continuous function, but it is a staircase.

Repair:

- An overflowing candidate now reports its exact rendered frontier cost. The
  next retry uses at most `used_tokens - 1`, crossing the current plateau while
  selecting the largest cheaper dependency-closed cut.
- If guided search is exhausted, a final minimum-closure proof still admits
  through the exact context gate or fails closed. The response reserve and all
  mandatory content remain non-negotiable.

Exact live replay:

- The failed G50T action-1 request now takes 6,400→3,654 in one rebuild, uses
  3,017 frontier tokens / 11 objects, retains all five current entities, one
  prediction, and the exact transition evidence reference, and occupies 15,472
  tokens including the 2,048-token reserve (912 headroom).
- Campaign aggregation now counts committed transitions recovered from error
  and timeout rows while still excluding pending actions and preserving
  completed-run-only score totals.

Status: contract and exact-live-replay verified; refreeze required.

## Checkpoint 12 — first frozen live outcome at `44ef930`

G50T, 360-second bound:

- 28 committed actions, one uncommitted pending action, zero levels.
- Both comparable frozen baselines committed 22 actions in the same 360-second
  window: +6 actions / +27.3% throughput.
- Time to action 28 improved from 527.7–536.5s to 336.0s (36–37% faster).
- Median committed-transition→next-demanded-Qwen-queue preparation fell from
  about 20.1–20.6s to 4.66s; the maximum fell from 51.6–56.9s to 6.1s even at
  14,362 graph objects.
- Eight Qwen calls completed with zero transport/parse errors. The baselines had
  six to eight errors in their comparable early calls. New execution spent more
  wall time on successful model inference yet still committed six more actions.
- The auditable chain contains 28 transitions/predictions/evidence records and
  five support/refute edges (three supports, two refutes). No identical
  consecutive no-change action and no decision/execution mismatch occurred.

Score did not improve on this game. The result promotes exact graph batching as
a generic runtime intervention, not as a competence claim. The active serial
cohort has continued to the click-mechanic games.

## Checkpoint 13 — command identity at the AR25 score boundary

Frozen `44ef930` outcomes before intervention:

- G50T: 28 commits / 0 levels.
- LF52: 11 commits / 0 levels, including two exact coordinate clicks.
- AR25: 27 commits / 0 levels.

AR25 reached the byte-identical state produced by the historical clearing
prefix `1, 2×11`. The historical run then used action 3 five times and cleared
at action 17. The current run's unmodified fallback at that state was also
action 3, but R2 ranked action 4 as the more novel probe and it worsened the
declared boundary gap 6→9.

The generic cause was found earlier in the same episode: a bounded fast-path
override executed simple action 2 while the controller retained fallback
command 3 internally. Transport was correct, but settlement paired
`action=2` with `command/effect_scope=3`, falsely consuming command 3's novelty
and corrupting causal attribution. The same pattern occurs in G50T; the stored
campaign corpus contains five unique fast-path decisions with stale internal
command identity across the two games.

Repair:

- Every resolved simple override now synthesizes and stores its exact command
  before the decision contract is persisted.
- Parameterized overrides without a frame-grounded exact command clear stale
  state and fail closed.
- Defensive resolution also synchronizes the internal command and contract, so
  decision, pending, execution, settlement, effect scope, and action-use
  attribution share one identity.

Status: generic contract suite green; same-state AR25 rerun pending. Historical
route success is comparison evidence only and is not encoded as a heuristic.

## Checkpoint 14 — same-state score recovery at `37ca449`

The frozen targeted AR25 rerun provides a controlled score result:

- It reproduced the byte-identical prefix `1, 2×11` and the exact common pivot
  digest from the failed `44ef930` episode.
- At the former stale-command boundary, executed action, exact command,
  decision contract, settlement command, effect scope, and action-use ledger
  all remained action 2.
- At the pivot, R2 selected action 3. Five action-3 successors matched the
  historical successful digest sequence byte-for-byte, and level 1 cleared on
  action 17.
- The failed build diverged from the same state to action 4, worsened its
  residual, and scored 0 after 27 actions. The corrected build scored 1 after
  17 actions.

The suffix was learned online: the first action 3 was an information probe;
successors then raised exact mechanism support/confidence and subsequent
action-3 decisions became progress eligible. No action route, hidden semantic,
or game-specific goal was added.

The six-minute worker ended with 22 committed actions, one uncommitted pending
action, and one cleared level; the five level-2 actions did not clear another
level. Status: promoted generic control intervention with exact same-state score
and causal-chain evidence; deeper-level transfer remains open.

## Promotion discipline

A campaign intervention is promoted only after:

1. its intended dataflow is visible in provenance;
2. a targeted contract or same-state comparison supports its causal effect;
3. a later frozen, mechanic-diverse run checks transfer and runtime regressions.

## Checkpoint 15 — frozen 25-game breadth at `62465d9`

The first pass completed across all 25 public games under one frozen 68-file
source manifest (`7ca8b7aa...`), with no source drift, replay failure, authority
violation, or completed Qwen transport error.

- 383 committed actions; 18 timeout-boundary pending actions were excluded.
- One real level clear: AR25, on the independently reproduced 17-action path.
  This is 1/25 games and 1/383 committed actions.
- Outcomes were 22 timeouts, two controller errors, and one clean completion;
  clean completion is a runtime status, not a score predicate.
- 132 coordinate clicks were committed across 17 games. Every click carried
  exact x/y data, current-frame region evidence, command identity, and effect
  scope through pending, execution, transition, and replay.
- All 408 canonical environment observations had valid ordered envelopes. 64
  packets across 13 games were multi-frame, preserving 967 ordered frames in
  total (maximum stack 42).
- The controller observed 307 changed and 76 unchanged successors. It emitted
  24 supports and six refutes, concentrated in six games; 19 games produced no
  prospective judgment.

Observable failure-layer coverage was broad: execution coverage 25/25;
animation evidence 13/25; identity support/limitation 10/15; mechanics
support/open 12/13; semantic evidence/repetition 14/11; exploration support or
no-change limitation 13/12; and success observed/not observed 1/24. This is a
failure taxonomy, not a claim that any one layer is the unique cause.

Throughput varied from two to 48 committed actions in the same five-minute
window. The exact graph batch intervention removed the demonstrated cumulative
replay slope, but perception fitting, semantic inference, and model latency
still produce large mechanic-dependent runtime differences.

## Checkpoint 16 — breadth-discovered boundary repairs at `ac3b73b`

The frozen pass exposed two generic failures after the external transition
substrate had become trustworthy:

1. SU15 had 27 exact grounded click candidates, but a repeated-no-change branch
   changed the selected action from simple action 7 to parameterized action 6
   after command resolution. The resolver correctly failed closed rather than
   fabricate coordinates. The repair atomically rebinds any post-resolution
   action mutation to an exact current-frame command and retains fail-closed
   behavior when none exists.
2. SP80 naturally entered GAME_OVER, durably committed an action-0 retry, and
   returned a playable successor with `full_reset=false` and unchanged score.
   Graph ingestion then failed because the v1.9 wrapper did not forward the
   explicit retry boundary. The wrapper now forwards `boundary_kind` without
   weakening its selected-judgment filter.

The same commit repaired score surfaces: committed levels recovered from
timeout/error ledgers now count, while pending actions remain excluded. The
post-hoc frozen oracle reports one level and AR25 as the clearing game without
altering runtime statuses or any failure-layer count.

Combined controller, action-command, request-admission, reset, v1.4, v1.9,
v1.12, analyzer, replay, and stored-request contracts passed. A real SP80
checkpoint correctly refused resume after source drift; the compatibility gate
was preserved rather than bypassed.

## Checkpoint 17 — current score boundary after breadth

Qwen scheduling was demand-driven and non-polling: 145 queued turns comprised
25 initial, 115 alias-only, four explicit-failure-only, and one overlapping
alias/failure demand. All 135 completed calls had valid JSON transport and no
transport error. Exact admission preserved at least 2,048 completion tokens.

The remaining bottleneck is semantic revision and causal conversion:

- 35/145 turns collapsed to the safe 59-token, zero-object attention frontier;
  all 28 completed calls at that frontier produced no accepted working note.
- Richer turns produced 82 notes from 107 completions, but 51/57 consecutive
  accepted proposal sets were canonically identical.
- Five turns were initially classified as unsupported/refuted revision demand;
  a later full-state audit showed that classification was caused by projection
  truncation, not authoritative unsupported semantics.
- Across 401 decisions, only 22 were goal-progress selections; 374 were
  information or discriminating probes. Actual progress was positive 22 times,
  negative 11 times, and zero 318 times.

The next intervention must first preserve support gates through bounded
projection. Separately, admission should recover the richest safe frontier
when capacity remains, without weakening the reserved completion budget.
Neither change should invent goals or infer action semantics from game IDs.
## Checkpoint 18 — live recovery of both breadth errors

Fresh focused runs on `0ad9caf` crossed the exact two pass-1 failure seams:

- SU15 reproduced the first five command/predecessor pairs byte-for-byte. On
  decision six, repeated-no-change control changed fallback action 7 to action
  6 and rebound a current-frame observed cell `(x=20,y=43)`. Decision contract,
  pending action, committed transition, command ID, effect scope, and payload
  grounding agree. The successor was playable, visibly changed, preserved a
  valid ordered five-frame envelope, and was graph-materialized. The old build
  raised before this action.
- SP80 naturally repeated the action-5 `NOT_FINISHED -> GAME_OVER` transition.
  The action-0 retry restored `NOT_FINISHED` with `full_reset=false` and levels
  unchanged. Its explicit `game-over-retry-reset` transition and environment
  evidence were materialized in the graph, after which a grounded coordinate
  action 6 committed and further graph/Qwen events continued. The old build
  crashed before graph materialization.

These runs promote both repairs from interface contracts to direct live causal
evidence. Neither changes a goal, action meaning, ranking heuristic, or game
parameter.

## Checkpoint 19 — preserve support through bounded semantic projection

The proposed evidence-addressed semantic-revision task exposed a prerequisite
defect before implementation: both compact projection tiers could discard
`control_status` and confirmation counts. In frozen AR25, KA59, and G50T
examples, a refuted settlement could therefore look unsupported after
truncation even while the active explanation was progress-eligible or had
positive confirmations.

The minimal repair retains only `control_status`, direct `confirmations`, and
`epistemic_evaluation.confirmations` through both bounded tiers. It changes no
scheduler or semantic authority. Forced-truncation contracts prove progress
and confirmed explanations suppress false failure routing while remaining
inside the 12KB bound. The larger semantic-revision protocol remains
unpromoted until it can consume causally sound projections.

## Checkpoint 20 — false-failure reclassification and truthful advice

A bounded evidence-addressed revision protocol was implemented behind the
corrected support gate, then removed before promotion when the full frozen
corpus showed it had no observed target. All five apparent failure demands
(AR25 one, G50T two, KA59 two) retained `PROGRESS_ELIGIBLE` control, unique
identity, confirmations, and supported mechanics in their authoritative full
decision blobs. Projection truncation alone had erased those gates. A fresh
KA59 run reproduced both refutations but correctly emitted no failure task.
The campaign therefore keeps the small projection repair and ordinary exact-set
stagnation guard, not an unneeded revision protocol.

A separate provenance repair distinguishes unauthorized R2 rankings from the
executed decision. In first-pass telemetry, 153/207 advisory selections differed
from the durable exact command. These labels did not affect execution, but the
advisory selection rule was persisted as executable graph rationale. Advisory
items now expose `advisory_selected`, `selected=false`, and
`execution_authorized=false`; unauthorized evaluator prose is stored separately
as `advisory_selection_rule`. Raw evaluator output remains intact and controller
behavior is unchanged.

Combined semantic, controller, integration, action-command, observation, and
stored-request suites pass. A future revision protocol requires genuinely
unsupported live evidence before promotion.

## Checkpoint 21 — exact-admitted recovery from empty attention

After the ordinary bounded frontier search exhausts, the controller now keeps
the already-admitted mandatory cut as an immutable fallback and tries exactly
one richer interpolated dependency-closed cut. The probe still passes through
the unchanged GGUF request admission and 2,048-token reserve. If it fails,
raises a frontier error, or adds no object, the previously built fallback is
returned by identity. Normal non-collapse paths never enter this branch.

An offline oracle reconstructed all 35 frozen first-pass 59-token/zero-object
turns from exact graph prefixes, scratchpad projections, visuals, and request
IDs. 34/35 recovered 5–12 objects (median 10) with exact reserve and 44–1,865
tokens of admitted headroom. G50T action 19 admitted no additional object and
correctly retained the exact mandatory fallback. There were zero context,
mandatory-binding, causal-packet, determinism, or admission failures.

## Checkpoint 22 — shadow click causal-footprint census

A new analysis-only tool replayed all 132 committed coordinate clicks from the
frozen first pass. It requires exact command grounding, decision/pending/commit
identity, blob integrity, ordered-frame digests, and settled-grid equality; any
violation abstains. It unions pixel changes across the ordered successor packet
and reports only the number of connected observed-change footprints.

- 56 clicks had one connected footprint across eight games.
- 26 had multiple disconnected footprints and remain ambiguous.
- 50 settled unchanged and abstain, even when transient animation occurred.
- All 132 passed transport/grounding/envelope integrity; 220 ordered frames and
  18 multi-frame click packets were consumed.

`unique` is deliberately shadow-only: it grants no game-rule, progress, graph,
or control authority. It establishes a measurable substrate for the next
held-out attribution experiment without changing an action.

## Checkpoint 23 — live attention recovery on RE86

RE86 was selected because all five of its frozen post-action Qwen turns had
collapsed to 59 tokens and zero graph objects. Under `9e21e47`, all five live
boundaries were nonempty: 11, 12, 10, 6, and 6 objects. The first two retained
frame, eight entities, relation set, and action proposals; both transported
cleanly and produced accepted working notes, whereas the frozen empty-frontier
calls produced none. Later cuts became smaller and prediction-focused but never
collapsed. Every cut remained dependency-closed with the configured 2,048-token
reserve and no semantic-failure protocol residue.

The third completed rich response was rejected by the pre-existing
action-language safety gate, apparently due to retrospective prose containing
“move left.” That is now a distinct compiler-classification question, not an
admission failure. The six-action focused run scored no level; the promoted
effect is improved usable semantic evidence, not score.

## Checkpoint 24 — retrospective evidence is not an action proposal

The RE86 action-2 response retained exact evidence and a valid alias but was
rejected because its scratchpad said “Previous action (move left) adjusted
positions.” The safety regex treated every opaque action token as a proposed
intervention, regardless of tense or clause role.

The frozen first pass contained 26 such rejections across 13 games (19.3% of
completed calls). All 26 matched retrospective outcome descriptions; none
recommended an executable action and none exceeded the scratchpad budget. The
broader artifact corpus showed the same pattern in 55 responses.

The compiler now exempts a bare `Action N` or directional move only when the
same bounded clause contains both an explicit previous/prior/last/latest/recent
action governor before it and a past-outcome predicate after it. Directive and
control lexemes remain unconditional failures, and any ambiguous or mixed
mention remains blocked. Exact RE86, corpus-derived history, mixed-directive,
and choose/select/execute/press/button/click contracts pass. This expands
evidence description, not Qwen's action authority.

## Checkpoint 25 — exact live safety reclassification

A second RE86 run reproduced the prior action-2 frontier exactly and received
byte-identical Qwen response content, including the retrospective “Previous
action (move left) adjusted positions but failed…” clause. Before the fix this
response compiled to zero accepted objects with
`working-note-safety-or-budget`; after the fix it compiled with two accepted
objects, zero rejections, and durably added ACTION_2's alias at the exact
transition evidence reference. No directive lexeme was present, and the goal
remained non-executable alignment semantics.

The following action-3 response likewise changed from safety rejection to two
accepted objects. Through that boundary, all four Qwen transports were valid
and accepted two objects each; command identity and the first three frontier
cuts remained unchanged. The run committed four actions and scored no level
before the focused deadline. Status: promoted recovery of semantic evidence on
the same model output, without a score claim.

## Checkpoint 26 — first final-regression failure followed immediately

The first latest-build regression was stopped during G50T when the same safety
boundary rejected “No visible change after action 1.” Thirteen actions had
committed with no command, settlement, advisory, animation, transport, or
frontier invariant failure; all five Qwen cuts were nonempty. The stop therefore
isolated a second retrospective grammar form rather than a controller failure.

The exemption now also accepts a bare action mention immediately governed by
`after`/`following` when the same bounded clause contains an observed past
outcome before or after it. Exact G50 prose compiles, while connector-only,
future, ambiguous, directive, and mixed forms such as “After Action 1 choose
Action 2” remain blocked. The broad freeze is restarted from the new commit;
the interrupted prefix is diagnostic evidence, not a completed cohort.

## Checkpoint 27 — close the observed retrospective grammar

The restarted freeze crossed G50T cleanly, then stopped at LP85's exact phrase
“fit_residual remains ... despite action 6. ... no visible change occurred.”
Through LP85, six games committed 46 actions with zero command, payload,
settlement, advisory, animation, frontier, transport, or runtime exception;
18/18 Qwen frontiers were nonempty. The sole compiler rejection was this valid
retrospective response.

Rather than enumerate another connector, the classifier now recognizes a bare
opaque action as history only when a known observed-outcome phrase is causally
adjacent within 140 characters, with no intervening action, modal/future
language, semicolon, or multiple claim boundaries. A parenthesized plural
action list is the only shared-outcome exception. Directive/control tokens
remain independently fatal per match.

All 57 formerly safety-rejected parsed responses in the stored breadth corpus
now classify as historical, while modal/future, choose, next-move, mixed-action,
prior-sentence, and ambiguous-selected adversarials remain blocked. Status:
contract-validated; exact LP85 live replay is the promotion gate.

## Checkpoint 28 — live LP85 historical-class validation

The focused LP85 run reproduced the first five grounded click commands and
successors exactly, including coordinates, command/effect-scope IDs, frame and
region grounding, rankings, observations, and prospective evidence. At the
same action-1 transition reference, Qwen produced a different but equivalent
historical form: “Action 6 produced no visible change.” It transported cleanly,
compiled with two accepted objects and zero rejections, and persisted a stable
ACTION_6 no-op hypothesis at that exact evidence. It contained no command,
payload, future, directive, or execution authorization.

Because upstream Qwen wording differed, this is a historical-language-class
validation rather than the byte-identical-response A/B achieved on RE86. The
exact old LP85 `despite action 6` clause is covered by the closed-corpus
compiler regression. Status: promoted safety classification with exact
execution/provenance control and an explicit model-output caveat; score remains
zero in the short run.

## Checkpoint 29 — uninterrupted closure freeze at `5235c1b`

The final immutable source completed a full first pass over all 25 games plus
two brief level-2 diagnostics within the 2,200-second global deadline.

First-pass closure results (excluding the two later level-2 diagnostics):

- 25/25 games attempted; 114 committed actions; zero worker errors, authority
  violations, or replay failures.
- All games hit the deliberately short 80-second deadline and none cleared a
  level. Four games committed zero actions, exposing remaining runtime/perception
  coverage cost rather than an interface exception.
- 137 exact decisions/pending actions and 114 exact commits; 44 grounded
  parameterized decisions, with every settled payload preserved exactly.
- 373 executable ranking rows and 132 advisory rows retained the explicit
  authority separation.
- 139 observation envelopes preserved 274 ordered supports, including 21
  multi-frame packets; all hashes, ordering, settled ordinals, and final grids
  recomputed exactly.
- All 64 pass-one Qwen queues were claimed and had nonempty frontiers (4–16
  objects). 50 completed calls had clean transport, valid JSON, and two
  accepted objects each: zero compiler or safety rejects, zero recorded
  admission failures, and zero false semantic demands. Fourteen claimed calls
  remained incomplete at their forced episode cutoff.

The closure pass is mechanically clean but scoreless; it does not supersede the
earlier five-minute-per-game score cohort. The authoritative campaign score result
remains AR25's exact 17-action level clear; the same-state recovery is separate
diagnostic evidence. The closure pass demonstrates that the final generic
fixes ran across all 25 public games without reopening the discovered execution
and telemetry defects.

## Final campaign theory of the boundary

The evidence now separates prerequisites from competence:

1. Mechanics can be observed and executed: clicks, ordered animation, retry
   RESET, command identity, deadlines, and replay are no longer hard-excluded.
2. Runtime overhead was materially reduced: exact graph batching removed the
   cumulative replay slope and safe frontier recovery eliminated nearly every
   empty Qwen context.
3. Correct causal identity can move score in the observed AR25 contrast:
   repairing stale command attribution removed the exact action-13 divergence,
   after which three repaired long-budget traces reproduced the same action-17
   clear. This is necessary-at-that-pivot evidence, not a general guarantee.
4. The dominant remaining score boundary is situated causal attribution and
   plan quality, especially for clicks. Broad access produced many changed
   successors but almost no prospective click judgments; the shadow census
   showed most apparent unique effects were distant global boundary carriers.
5. Semantic repetition is real, but the campaign's five supposed explicit
   semantic failures were projection artifacts. R2 should not churn a useful
   goal because one horizon prediction refuted.

The smallest next experiment is therefore shadow-first causal correspondence
for clicks, requiring replicated structural source/effect relations, negative
command controls, and held-out prospective confirmation before probe-only
promotion. Structural cross-level transfer remains high eventual leverage but
has only one authoritative level-2 boundary and must remain probe-only until
more local confirmations exist.

## Checkpoint 30 — final realistic-budget score replication

The final source `a101c72` was frozen for a 300-second-per-game score cohort.
Six games finalized before the parent was stopped after its next worker ceased
progressing: G50T 26/0, LF52 9/0, AR25 19/1, FT09 16/0, LS20 12/0, and LP85
20/0 (actions/levels). Aggregate: 102 committed actions, one level, six
timeouts, zero errors or authority/replay failures.

AR25 independently reproduced the exact score boundary under all final changes:
action 17 completed the same `1, 2×11, 3×5` learned trajectory, committed the
known successor digest, and incremented levels to one. Actions 18–19 continued
in level 2. No route was encoded. The repair removed the previously observed
stale-command pivot, and the resulting environment-confirmed trajectory was
then reproduced under the final source.

The other five games matched or modestly exceeded primary action depth without
scoring. Completed Qwen calls remained transport-clean and accepted, and
frontiers remained nonempty. This strengthens the causal score result while
also confirming that one generic control repair has not yet converted broad
mechanic access into broad score.

On the same six games, the primary build used 33 queued / 31 completed Qwen
calls and accepted 23 calls (46 objects); the final build used 27 / 25 and
accepted all 25 calls (50 objects). It therefore queued 18.2% fewer calls while
producing 8.7% more accepted objects.
The primary slice had seven retrospective-language false positives, one stale
proposal rejection, two empty frontiers, and three projection-induced semantic
failure demands. The final slice had none of those failures. This is strong
evidence that the final cognition path delivers denser usable evidence, not
evidence that it broadly improves score.

## Checkpoint 31 — AR25 level-boundary transfer audit

The authoritative carried level-2 boundary is AR25 digest `5fcedd77...` after
the action-17 clear. `advance_level()` resets situated bindings and role
trajectories while retaining only action effects, action-use counts, and
explanation confirmation/refutation history. At the next carried decision,
correspondence was unique but both role identities were UNINITIALIZED,
`control_eligible` was false, and the mechanism was UNKNOWN with no supported
model. Action 4 therefore had only PROBE_ELIGIBLE authority and null predicted
progress; historical evidence did not silently become progress control.

The available stored fresh level-2 episode starts from digest `2b21f363...`, a
different layout, so it is not a matched fresh-state comparator. No claim about
relative action savings or cross-level effect conflicts is promoted from that
unmatched trace. The defensible result is narrower: situated role identity did
not transfer at the observed successful boundary, and any structural backoff
must remain probe-only until tested on an exact matched start.

Final verification reran the dynamically loaded suites in isolated processes:
68 v1.4 tests, the full 16-test v1.9 suite, 14 v1.12 tests, 92 leaf contracts,
15 command and observation-envelope tests, 2 stored request-budget tests, and
18 breadth analyzer/click-shadow tests. All 225 passed; `git diff --check` was
clean.
