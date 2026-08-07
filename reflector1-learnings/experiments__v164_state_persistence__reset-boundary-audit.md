# v164 operative reset-boundary audit

## Operative path

The released notebook embeds the overlay hashed in
`submission/kaggle_v164/release-manifest.json`. The overlay's official adapter
constructs exactly one `SymbolicPolicy(deployed_config())` in
`agents/templates/reflector_agent.py:28-35`. The starter `Swarm` constructs one
agent per game at `agents/swarm.py:69-89` and each agent's loop retains that
object for the whole game. Each returned frame is appended and learned at
`reflector_agent.py:51-55`. Therefore kernel start and each game start create a
clean policy; ordinary steps, resets/deaths, and level advances do **not** create
a new policy.

At every observation, `SymbolicPolicy.observe` mutates the Mind and explorer
(`reflector/runtime/policy.py:223-245`). `choose_action` additionally mutates
decision provenance, action counters, explorer arbitration/planning state, and
epochs (`policy.py:247-318`). On `NOT_PLAYED`, `GAME_OVER`, or `NOT_STARTED`, it
emits action 0 and clears only `mind.last_experiment` and `mind.last_plan`
(`policy.py:251-258`). It does not replace any store.

## Boundary table

| State component | Kernel/game start | Level advance | Death / `GAME_OVER` | Ordinary step |
|---|---|---|---|---|
| transition schemas/statistics | new empty store | persists and updates | persists and updates | updates |
| concepts/object roles | new empty store | persists; episode role lists reset selectively | concepts persist; episode role lists clear | updates |
| transition/control models | new empty stores | many models retain controls/algebras; level-local fields reset | retry-scoped models may be retained | updates |
| hypotheses | new empty store | persists | persists | updates |
| options/strategies | new explorer | successful programs/schemes may be compiled and retained; cursors reset | schemes persist; retry cursors/state reset selectively | invoked/updated |
| episodic memory | empty | some episode lists, current plans, and grounded caches reset; global visit graph and schema evidence persist | several episode lists/plans reset; visit/schema evidence persists | accumulates |
| learned parameters/statistics | zero | persist except counters explicitly marked per-level | mostly persist; selected per-retry counters reset/increment | update |
| action-affecting caches | empty | portfolio cache and learned stores persist; numerous grounding caches clear | selective clear/retain | update |
| planner state | new planners | `last_plan` is overwritten; specialized planners selectively reset | `last_plan` cleared only when reset action is selected; specialized retry resets run | update |
| novelty/failure records | empty | global state/edge/attempt records persist; `level_failures` becomes zero | global records persist; `level_failures` increments | update |

The exact explorer level transition is detected by an increase in
`levels_completed` at `reflector/core/exploration.py:1510-1513`. It retains a
successful program when enabled (`1514-1526`), clears enumerated episode-local
structures (`1527-1572`), and explicitly retains phase-topology action algebra
(`1573-1574`). On death it performs a different retry reset
(`1575-1616`), retaining pivot models (`1605-1607`), phase topology under a
same-level scope (`1579-1583`), and potentially cross-retry maturity.

Important concrete examples are `PivotGoalPlanner.reset_level(retain_model=True)`,
which preserves its learned edges/effects (`reflector/core/pivot_goal.py:299-307`),
and `PhaseTopologyPlanner.reset_level(retain_action_algebra=True)`, which derives
and retains an inherited action algebra before clearing current grounding
(`reflector/core/phase_topology.py:574-648`). This is verified runtime behavior,
not inferred from configuration names.

## Instrumentation boundary

The harness hashes all mutable policy/Mind/explorer/trace components separately
and as one canonical serialization. Snapshots are emitted before the first action
and after the completion observation of every reached level, plus run final.
Transition schema IDs (`s-...`), operative content-addressed scheme record IDs,
and lifecycle IDs form the stable schema catalog. Pickled snapshots accompany
canonical JSON so a behavior-changing result can be replayed from the exact
serialized object graph.

