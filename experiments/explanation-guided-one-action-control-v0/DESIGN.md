# Explanation-Guided One-Action Control v0

## Status

Implemented and validated on `ar25`; not preregistered. See `README.md` for
commands and measured results.

## One-sentence specification

> At each decision boundary, R2 uses grounded, falsifiable explanations to
> choose the single legal action that best advances a live objective, resolves
> a decision-relevant uncertainty, or both; the environment settles the
> prediction before another action is chosen.

## Invariants

1. Commit exactly one primitive environment action per decision cycle.
2. Never execute an action queue.
3. Record a machine-checkable prediction before every action.
4. Return every successor observation to R2 before choosing again.
5. Only environment observations confirm or refute predictions.
6. Qwen may propose meanings and objectives but may not name actions.
7. R2 selects; the arbiter authorizes; the executor performs.
8. Unknown is valid. Never disguise a fallback as a justified prediction.

## Definitions

### Fact

A typed claim derived deterministically from an environment observation or
transition. It cites the source observation or transition.

```text
Touches(S,W)
Anchor(S)=(12,20)
ObservedEffect(A2,S)=Translate(0,1)
```

### Hypothesis

An unsettled claim, such as `S is controllable`.

### Objective

A grounded hypothesis about what change constitutes progress.

```text
measure: ContactResidual(S,W)
direction: Decrease
completion: Touches(S,W)
```

An objective is revisable; it is not automatically the true game goal.

### Explanation

An explanation is a typed control hypothesis:

> In context C, action A should cause observable result O, and O matters to
> objective G.

It has these required fields:

| Field | Meaning |
| --- | --- |
| `context` | Grounded preconditions that hold now |
| `action` | One opaque legal action |
| `prediction` | Observable one-step successor claim |
| `objective_change` | Why the successor is useful or harmful |
| `scope` | Conditions under which the explanation applies |
| `evidence` | Supporting, refuting, and unresolved transitions |

Natural-language commentary is not an explanation. It may summarize one, but
only the typed object enters control.

### Progress action

An action predicted to improve or complete a live objective.

### Information action

An action for which live explanations predict different observable results.

### Dual-purpose action

An action predicted to make progress and distinguish explanations.

### Checkpoint

A predicate evaluated on the real successor, for example:

```text
AnchorAfter(S)=AnchorBefore(S)+(0,1)
ContactResidualAfter(S,W)<ContactResidualBefore(S,W)
TouchesAfter(S,W)
LevelCountAfter>LevelCountBefore
```

## Authority

| Component | May do | Must not do |
| --- | --- | --- |
| Qwen | Propose semantic, mechanic, role, and objective hypotheses | Name, rank, or commit actions |
| R2 | Ground hypotheses, predict actions, select one action, settle predictions | Create empirical evidence |
| Arbiter | Validate and commit R2's selected action | Replace it with another action |
| Executor | Submit one authorized action and capture its result | Choose, repeat, repair, or continue actions |
| Environment | Produce authoritative observations and outcomes | — |

The biological analogy is hierarchical delegation: broad cognition proposes
meaning; a control system selects an intervention; lower machinery executes it
and returns sensory feedback. It does not imply autonomous chain execution.

## Input and output

### Decision input

```text
current observation and digest
legal actions
grounded facts
live objectives
live explanations
transition history
action-use and risk history
```

### Decision output

Either one `ActionDecision` or `NO_JUSTIFIED_ACTION`.

```json
{
  "decision_id": "D18",
  "basis_revision": 281,
  "observation_digest": "...",
  "selected_action_id": 2,
  "mode": "progress_and_information",
  "objective_ids": ["G1"],
  "explanation_ids": ["H1", "H2"],
  "checkpoint": {
    "kind": "entity_displacement",
    "entity_id": "S",
    "expected_delta": [0, 1]
  },
  "alternative_outcomes": [
    {"checkpoint": "S does not move", "favors": ["H2"]}
  ],
  "risk_class": "reversible"
}
```

## Deterministic algorithm

### 0. Settle the previous action

If a previous action exists:

1. evaluate its checkpoint on the new observation;
2. classify each prediction as `supported`, `refuted`, or `unresolved`;
3. classify objective change as `positive`, `neutral`, `negative`, or
   `unknown`; and
4. write a settlement record.

Do this before constructing the next decision.

### 1. Build the live explanation set

Keep an explanation only when:

- its context is grounded now;
- its dependencies are live;
- it remains within scope;
- it is not hard refuted; and
- its one-step prediction is checkable.

### 2. Predict every legal action

For each legal action, ask every live explanation that models it to return:

```text
checkpoint
objective change: complete | positive | neutral | negative | unknown
risk: none | reversible | reset | terminal
```

`Unknown` is not `neutral`.

### 3. Reject inadmissible actions

Reject an action if it is:

- illegal or stale;
- dependent on an invalidated object;
- missing an executable checkpoint; or
- predicted to cause terminal/reset risk without an explicit risk-taking
  objective.

### 4. Choose the first nonempty action class

1. **Safe completion** — at least one live explanation predicts milestone
   completion and none predicts hard risk.
2. **Robust progress** — every live explanation that models the action predicts
   nonnegative change, and at least one predicts positive change.
3. **Progress plus information** — a grounded explanation predicts progress
   while competing explanations predict observably different successors.
4. **Pure information** — no progress action is available; the action separates
   explanations relevant to a future control decision.
5. **Safe unknown probe** — no useful model exists; the action is legal, has no
   known hard risk, and has not already produced the same unresolved result in
   the same grounded state.

If all classes are empty, return `NO_JUSTIFIED_ACTION`.

### 5. Break ties in this order

1. lower risk class;
2. more live explanation pairs separated by observable outcomes;
3. fewer repetitions of the same grounded state-action effect;
4. more direct environment support;
5. lower opaque action ID.

Persist every tie-break value.

### 6. Persist before acting

Write the decision, selected explanation/objective dependencies, primary
checkpoint, alternative outcomes, and risk classification before action
commit.

### 7. Execute once

The arbiter validates the record. The executor submits the selected action
once, captures every returned frame plus the settled observation, writes the
result, and stops.

The loop then returns to step 0.

## Wall example

Facts:

```text
Shape(S)
Stationary(W)
Disjoint(S,W)
ClearanceRight(S)=1
```

Objective:

```text
G1: decrease ContactResidual(S,W) until Touches(S,W)
```

Explanations:

```text
H1: if ClearanceRight(S)>0, A2 moves S right one cell.
H2: A2 is blocked in the current configuration; S will not move.
H3: A2 controls another object.
```

A2 is dual-purpose:

- movement of S advances G1 and supports H1;
- no movement supports H2;
- movement of another object supports H3.

R2 selects A2. The executor performs A2 once. The successor settles H1–H3
before any next action is selected.

An unchanged grid does not automatically mean no effect. Settlement also
checks animation, legal actions, counters, progress, terminal state, and
possible latent-state change. Repeating A2 requires a new justification.

## Replanning

The external loop always executes one action and then decides again.

Internal search may produce a multi-step route, but the route is advisory. Its
suffix is reused only after validation against the new workspace state.

```text
plan internally
  -> execute one action
  -> observe
  -> validate or recompute
  -> choose one action again
```

Cheap deterministic prediction may run every cycle. Qwen is called only when
semantic interpretation, objective formation, or representation needs work.

## Bounded Qwen working note

Qwen may maintain one natural-language `working_note` containing:

- current interpretation;
- current objective hypothesis;
- open questions;
- recent contradictions; and
- cited workspace object IDs.

Rules:

1. Maximum 512–1,024 model tokens.
2. Rewrite instead of appending indefinitely.
3. Retain old versions in the immutable ledger.
4. Include basis revision and dependencies.
5. Mark stale when a dependency is invalidated.
6. Give all claims empirical support zero.
7. Forbid action IDs, ordering, and selection.

The note helps Qwen and a human observer. It does not control the environment.

## Arcade log

Display the same sequence for every action:

```text
observation
Qwen working note
live explanations and objectives
legal-action predictions
selected action and checkpoint
arbiter result
animation and settled successor
prediction settlement
updated explanations and objectives
```

Visually distinguish environment facts, R2 hypotheses/predictions, Qwen's
unverified note, and committed actions.

## Current substrate and additions

PCW v1.16 already has observations, transitions, grounded objects, masks,
relations, correspondences, action-conditioned relative deltas, one-step
predictions, Shadows, evidence, contradictions, and replay.

Required additions:

1. explicit objective records;
2. entity-level action effects;
3. state-dependent preconditions;
4. retention of zero-delta/no-op outcomes;
5. directional clearance and collision predicates;
6. typed successor checkpoints;
7. the deterministic selection gates above; and
8. bounded Qwen working-note storage.

## Experimental question

Does this explicit explanation-to-action contract improve one-step prediction,
decision-relevant ambiguity reduction, grounded objective progress, avoidance
of redundant/harmful actions, and level completion per real action relative to
the current explanation ranking—without giving Qwen action authority or adding
open-loop execution?
