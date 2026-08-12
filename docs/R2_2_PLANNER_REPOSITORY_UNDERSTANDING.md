# R2.2 planner repository understanding

Status: audit written before implementation on 2026-08-11; implementation
boundary appended afterward.

## Current control path

`src/reflector2/r2/experiment.py` installs one canonical runtime for Arcade and
headless runs. `LiveRuntime` fits the current settled frame with
`FrameSchemaObserver`; `OneActionController.plan()` obtains exact legal
`ActionCommand` objects and asks `FrameSchemaObserver.rank_actions()` to bind
the accepted semantic verb proposals to current regions.

For each situated verb binding and exact command, the observer joins the
current potential to command-scoped empirical actor/target translation effects,
simulates one successor, and materializes the existing causal-effect,
preferred-completion, progress, and explanation bindings. Ranking applies the
authoritative hard order `PROGRESS_ELIGIBLE > PROBE_ELIGIBLE > INELIGIBLE`.
The controller may use the bounded preferred-policy fast path after repeated
confirmed settlements, but it still selects and predicts one action.

Immediately before transport, `LiveRuntime.before_action()` calls
`FrameSchemaObserver.commit_prediction()` with the final exact command and
explanation. The environment executes that one command and returns an ordered
observation envelope with one settled successor. `settle_action()` first tests
role correspondence, then attributes command-scoped effects, measures actual
potential progress, confirms/refutes the one-step prediction, and clears the
pending prediction. Fast-path authority consumes that settlement and revokes
on the first mismatch or protected-invariant failure.

## Planner attachment point

The narrow attachment seam is inside `FrameSchemaObserver.rank_actions()`
after current situated one-step candidates and supported effect models have
been constructed, but before the final ranked action becomes the controller's
decision. At that point R2 already owns all authoritative inputs: the active
explanation/verb binding, immutable predecessor role snapshots, exact legal
commands, measurable potentials, supported command-scoped effects, frame
bounds, and static observed occupancies.

The planner should consume immutable projections of those objects, recursively
compose their already-supported translations, and return a prospective
`ControlFactorization` plus plan certificate. It must not call the schema
learner, mutate support counters, install predicted regions in the empirical
workspace, or set `pending_prediction`. Only the chosen first command is
rebound to its existing one-step explanation. The existing
`commit_prediction()` seam remains the sole point that makes that prediction
settleable.

## Existing objects to reuse

- `ActionCommand` is the exact intervention identity and payload authority.
- Situated control explanations carry grounded roles, verb/potential,
  predecessor snapshots, mechanism support/confidence, successor projection,
  protected identity checks, and the one-step observable checkpoint.
- `action_effects` / `level_action_effects` and `_effect_model()` are the only
  learned transition authority. The planner needs a read-only snapshot of
  effects that already meet an explicit support/confidence gate.
- `_simulate_translation()` and `_measure()` define the current limited
  executable model and potential vocabulary. Planner adapters should reuse
  their semantics rather than add game rules.
- The existing role trajectories, settlement, mutual-occlusion factorization,
  `FastPathAuthority`, runtime prediction commit, observation envelopes, and
  durable decision/settlement telemetry remain authoritative.
- The recursive schema workspace remains the source of explanation bindings
  and shadows. Planner states are prospective values derived from them, never
  workspace observations or support.

## Code that must not be duplicated

The planner must not create another perception pipeline, region identity
tracker, effect learner, schema/support ledger, semantic goal compiler, action
transport, pending-prediction store, settlement path, or fast-path authority.
It also must not duplicate the inherited PCW planner or encode an AR25 route.
The only new machinery is bounded deterministic composition, milestone-shadow
derivation, result ranking, and an auditable certificate.

## Evidence informing the experiment

R2.1 documents three relevant AR25 boundaries: greedy control remained coherent
after roles collapsed to one-pixel fragments; approach-to-contact reached
`boundary_gap = 0` before identity failed under overlap; and a stale
command/effect-scope mismatch at the byte-identical `1, 2 x 11` prefix made the
failed controller choose action 4 instead of the action-3 suffix that later
cleared on action 17. The repaired build reproduced the 17-action clear three
times. These establish identity, settlement, and one-step-control boundaries,
not planner value.

The recent legacy `arc-traces/native-shared-qwen-ar25-v10` and `v11` runs did
not reach a matched planning result: both ended in model-context overflow and
reported zero completed games. The Kaggle insight corpus independently
prioritizes milestone-space planning, explicit expected observations, action
efficiency, and common-start paired evaluation. It also cautions that a single
public-game clear is weak evidence.

Therefore the first experiment must freeze the current one-step arm, clone the
same grounded workspace and learned support into the planner arm, and fork at
stored intermediate states. Planner success requires a different first command
whose real successor settles and yields better environment-grounded progress
or completion. A pretty internal route, node count, or repeated 17-action clear
without causal divergence is not success.

## Implemented modular boundary

The generic package is `src/reflector2/planner`, deliberately outside
`reflector2.r2`. It knows only immutable problem/result dataclasses and four
callbacks (`transition`, `measure`, `invariants_hold`, and `state_key`). Its
`PlannerBackend` protocol permits alternate search implementations without
changing the R2 adapter. `FrameSchemaObserver` constructs the situated problem
and accepts an injected backend; R2 retains all empirical learning, action
commit, environment settlement, and authority decisions.
