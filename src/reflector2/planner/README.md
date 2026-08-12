# Reflector planner interface

This package is controller-agnostic. It imports no R2 modules and owns no
perception, evidence, identity, action transport, or environment state. A
controller adapts its current state and supported mechanisms into a
`ControlProblem`, then supplies any backend implementing:

```python
class MyPlanner:
    name = "my-planner-v1"

    def search(self, problem: ControlProblem, config: PlannerConfig) -> SearchResult:
        ...
```

R2 injects the backend at its adapter boundary:

```python
observer = FrameSchemaObserver(
    planner_config={"max_depth": 6},
    planner_backend=MyPlanner(),
)
```

`BoundedBestFirstPlanner` is the default. `NoPlanPlanner` delegates every
decision to the host's original controller, so `backend: fallback-only-v0` and
`backend: bounded-best-first-v0` are direct old/new configuration choices.
Alternate implementations must honor
the same hard budgets and epistemic contract: prospective states are not
evidence, only supported effects may be composed, and a result can authorize
only its first command. Environment settlement remains the controller's job.

`ModelPlanner` is a third backend. It accepts either `QwenPlanningModel` or
`LunaPlanningModel`, both over the same structured-invoker protocol. The model
may propose command IDs, but the backend deterministically replays every edge
through the supplied transition/invariant callbacks and rejects unsupported,
over-budget, or milestone-free output. A model response therefore cannot grant
itself action authority.

R2's `planner_wiring.build_planner_backend()` connects these classes to the
existing provider-neutral model transport. Configuration examples:

```json
{"backend": "fallback-only-v0"}
{"backend": "bounded-best-first-v0"}
{"backend": "model-qwen", "model_max_tokens": 512}
{"backend": "model-luna", "model_max_tokens": 512,
 "model_reasoning_effort": "medium"}
```

The Qwen/Luna choice is an adapter choice; endpoints and credentials continue
to come from R2's existing resolved model profile.

The stable interchange types are `ControlProblem`, `SupportedCausalEffect`,
`MilestoneShadow`, `ControlFactorization`, `SearchResult`, and `PlannerConfig`.
All controller-specific semantics enter through the problem's transition,
measure, invariant, and state-key callbacks.
