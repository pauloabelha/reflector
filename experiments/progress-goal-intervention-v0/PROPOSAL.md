# Progress-goal epistemic intervention lab v0

## Why

The shared workspace can carry schemas, bindings, predictions, criticism, and
environment evidence. The verified ar25 run used that machinery to complete a
level. On wa30, however, live Qwen chose a uniquely grounded alignment proxy;
R2 tested all five opaque interventions and observed that every one preserved
the proxy residual. The system had no language for the actual game objective.

wa30 is now explicitly consumed oracle-development data. Source inspection and
a fresh oracle play verified level 1 in 26 actions. The task is a generic
pickup–carry–deliver problem: one distinctive actor, an equivalence class of
portable objects, and a larger target capable of containing the class.

## Causal question

What is the smallest support-zero workspace object that lets the existing
grounded system enter and complete the game?

Four fresh arms share an identical fixed calibration prefix and action budget:

1. `null_writer`: no mock object.
2. `sham_goal`: equal-size/salience but nonterminal declarative object.
3. `generic_goal_unbound`: variable-only bounded `GoalPotential` AST.
4. `generic_goal_oracle_bound`: the same AST plus a nontransferable situated
   development binding.

The candidate AST is action-free:

```text
roles:
  actor = DistinctMember(OutlineEquivalenceClass)
  items = RepeatedInteriorSubclass(same class, excluding actor)
  target = CapacityCompatibleRegion(items)
potential:
  OutsideCount(items, target)
preferred_operator: Decrease
terminal: Equals(OutsideCount(items, target), 0)
```

It contains no game, color, coordinate, entity, action, or trajectory constant.
The bound arm stores concrete bindings separately with provenance
`ORACLE_WA30_DEV`; they can never be transferred. Both objects begin with
empirical support zero. Only environment transitions may confirm predictions.

## Controller boundary

After the common calibration prefix, R2 may infer opaque translation effects
from directly observed actor displacement. The remaining simple intervention
is an interaction candidate, not trusted semantics. A generic symbolic planner
may test it only at an inferred actor–item interaction pose, then use observed
joint motion to establish carrying. It plans approach, pickup, transport into a
target slot, and release. No oracle action sequence is available to the
controller.

## Primary result

An arm passes only by completing level 1. `generic_goal_oracle_bound` must do so
within 40 total actions, replay exactly, and expose object→binding→subgoal→
action→transition→progress lineage. A completion by the unbound arm is stronger:
it localizes the missing capability to the generic goal object/grounder rather
than oracle role binding. Null or sham completion removes attribution.

This is not a generalization claim. After identifying the minimal winning
object, only its action-free generic AST may be frozen. A different game must
then be mechanically selected before frame inspection and solved unchanged for
the next genuine transfer result.
