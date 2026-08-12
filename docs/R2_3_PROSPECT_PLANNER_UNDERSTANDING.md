# R2.3 ProspectPlanner repository understanding

This audit was written before R2.3 production changes. It distinguishes current
implemented behavior from the proposed extension.

## 1. Current authority path

The configured semantic model writes two different products. Its five-field
`model_scratchpad`, including `game_objective`, is unverified working state and
does not enter control. Structured `workspace_write.goal_proposals` and
`abductive_compositions` are proposals only. The R2 compiler in
`src/reflector2/r2/scratchpad.py` validates their shape and citations; the
recursive adapter in `r2_1_adapter.py` then binds roles to the current frame,
measures a potential, joins supported command-scoped effects, and constructs
candidate situated explanations.

For each eligible situated actor/target/explanation group,
`FrameSchemaObserver._search_control_factorizations` freezes region snapshots,
supported actor/target translations, static occupancy, frame bounds, measures,
and invariant/state-key callbacks into a controller-neutral `ControlProblem`.
The injected `PlannerBackend` receives only that read-only problem. It imports
no R2 module, owns no graph or ledger reference, and cannot execute an action.

If the backend returns a factorization, R2 maps its first command ID back to an
already-grounded candidate, creates a prospective `plan_certificate`, promotes
that one candidate to `PLAN_ELIGIBLE`, and ranks it above the original
`PROGRESS_ELIGIBLE`/`PROBE_ELIGIBLE` fallback. `OneActionController` resolves
the exact command and payload, persists the same identity through the decision
contract and pending event, and submits exactly one intervention to ARC.

The environment returns an ordered observation envelope. R2 settles role
identity, the command-scoped mechanism, and the measured potential from the
real successor. `settle_plan_certificate` always invalidates the continuation
and requires replanning. Only this environment settlement changes effect or
explanation support. A confirmed preferred first edge may independently count
toward the existing bounded fast path after its certificate is removed; no
planned route, depth, or hypothetical node enters that empirical state.

In short:

```text
semantic proposal (zero authority)
  -> R2 compile, ground, and freeze ControlProblem
  -> planner computes hypothetical structure (zero empirical authority)
  -> R2 validates/ranks one exact grounded command
  -> ARC executes one command
  -> R2 settles only the observed successor and discards the continuation
```

## 2. What BoundedBestFirstPlanner optimizes

`derive_milestones` projects a bounded frontier consisting of the active
residual's terminal value and an immediate preferred-orientation milestone.
The deterministic search composes only effects meeting minimum support and
confidence, rejects inapplicable or invariant-breaking successors, and ranks a
node lexicographically by:

1. any terminal milestone reached;
2. any milestone reached;
3. total active-observable progress from the initial state;
4. weakest path confidence;
5. accumulated risk;
6. shorter depth;
7. stable command identity.

Visited-state pruning retains the shallowest occurrence of a prospective state;
frontier, depth, and expansion bounds are hard. A `ControlFactorization` ends at
the best node which satisfies one of these explanation-derived milestones.

## 3. Why deterministic AR25 plans did not diverge

The AR25 experiment held frame, explanation/role grounding, supported effect
table, and budgets fixed. Bounded search found depth-3/4 supported translation
compositions and all eight executed first shadows settled correctly, but its
first actions exactly matched one-step R2 at all three forks.

This follows from the objective, not from lack of search depth. Both the
one-step controller and the milestone search prefer decrease of the same active
verb residual. The planner can route around a represented obstruction, but a
mere residual decrease already satisfies its nonterminal milestone. It has no
separate representation of whether the successor admits a supported route to a
contract-relevant verb completion, how many such routes remain, or whether the
completed verb is relevant to level completion. Under AR25's available
translation model, deeper search therefore reproduced the locally best first
step. Around contact, both controllers reached the same missing identity and
merge/split dynamics boundary rather than inventing unsupported edges.

The Qwen planner's one adverse divergence proves only that validated alternate
compositions can change control. It supplied no goal-respecting reason for the
regression and produced no score effect.

## 4. Where terminal semantics currently stop

R2 strongly represents situated verb progress and a verb-local terminal such
as `fit_residual = 0`. The scratchpad may describe the game objective, but that
prose is deliberately outside action ranking. No current prospective,
evidence-cited relation represents:

```text
VerbTerminal(FIT) -> EnvironmentTerminal(level completion)
```

Level completion is available retrospectively as environment evidence and can
trigger explanation consolidation. Consolidated schemas restart with zero
empirical support and fresh-binding/probe-only authority. Consequently the
system currently distinguishes and settles local potential changes, but does
not prospectively distinguish verb completion reachability from game-objective
relevance.

## 5. Safe R2.3 attachment point

The minimum `GoalContract` belongs on the R2 side of the boundary. R2 may
compile a semantic proposal into a typed, evidence-cited hypothesis whose
status is `OPEN`, `SUPPORTED`, or `REFUTED`; only exact environment settlement
may change that status. The v0 relation is deliberately narrow: one grounded
verb-terminal class may contribute to one observable environment-terminal
class, with explicit evidence citations, provenance, and a countercondition
for verb completion without the expected environment terminal.

R2 should freeze a read-only projection of the active contract into
`ControlProblem`. The planner may then derive `GoalProspect` summaries from the
problem's callbacks and supported effects: terminal reachability/depth,
bounded factorization count, weakest support/confidence, unresolved
requirements, protected invariants, identity risk, and local orientation.
These summaries and their hypothetical paths remain certificate material only.
They must not reference or mutate the R2 ledger, support counters, schema graph,
role grounder, or environment transport.

`ProspectPlanner` attaches as another `PlannerBackend`, reusing the existing
transition/invariant/state-key substrate. Its key ranking distinction is that a
locally adverse first edge can outrank local progress only when the successor
strictly improves explicit supported terminal factorability (for example,
unreachable to reachable). R2 still maps the result to an existing grounded
candidate and authorizes exactly its first command. Settlement keeps the
existing invalidation path and additionally lets R2 adjudicate a contract only
when cited verb-terminal and environment-terminal observations actually occur.

This adds prospective control structure without expanding model authority or
creating a second epistemic engine.
