# Results: Prospective Context Spinoff Control

## Outcome

**Pass on the selected case.** An automatically discovered predecessor
condition changed the top action from opaque `ACTION_2` to opaque `ACTION_3`.
From independently reconstructed copies of the identical real state,
`ACTION_2` made no level progress while `ACTION_3` completed level 1. The
child's prospectively emitted structural-change shadow was reified.

## Game and diagnostic

The case is public game `ar25`, level 1. The established Reflector run reaches
two of eight levels, then spends most of its remaining budget on ineffective
actions, so this is a genuine progress-then-ranking-failure case. Current R2
already forms generic outline/contrast relation schemas on this game.

The first 16 transitions of the existing successful level-1 trajectory were
replayed through current R2. The level-completing transition was withheld from
learning. At the decision point, baseline and treatment predecessor frames had
the identical SHA-256
`10c623b65d4685c4951088ecde882989f1c370f31d7d795c1e26fdbfaf66d1ab`.

## Exact schemas

Parent `4dd44c2c187a681e2c8079ec0c9c79bcdc599b87829ea73cf326c5df191e23cc`:

```text
After(?v0, ActiveSchema, ?v1)
Before(?v2, ActiveSchema, ?v3)
Codomain(?v0)
Domain(?v2)
Intervention(?v4)
```

Child `e4d3812a7ae5f3c0efd59918f0d45ca3218e167384dd1e3fb8f88843d8b197b0`:

```text
After(?v0, ActiveSchema, ?v1)
Before(?v2, ActiveSchema, ?v3)
Before(?v2, BindingAbsent,
  38bac99b151198744c9ea62355a77c6116ef9493de6e678115dc8d4772385454)
Codomain(?v0)
Domain(?v2)
Intervention(?v4)
```

The parent remains in the graph. A `spinoff` edge from parent to child records
the specialization.

## Discovered context

The bounded search considered only established depth-0 binary relation schemas
and their current R2 `Binding` presence/absence. It selected absence of:

```text
SameInteriorContrast(?v0, ?v1)
```

Schema hash:
`38bac99b151198744c9ea62355a77c6116ef9493de6e678115dc8d4772385454`.
The condition had two earlier matching predecessors; both supported
`ACTION_3`, giving purity `2/2 = 1.0`, strictly above the unspecialized parent's
`11/16 = 0.6875`. No game ID, level ID, coordinate, palette interpretation, or
object-role label entered the search or ranking.

## Rankings

| Rank | Parent only | Support | With child | Child support | Parent support |
|---:|---:|---:|---:|---:|---:|
| 1 | `ACTION_2` | 11 | `ACTION_3` | 2 | 4 |
| 2 | `ACTION_3` | 4 | `ACTION_2` | 0 | 11 |
| 3 | `ACTION_1` | 1 | `ACTION_1` | 0 | 1 |

## Prospective prediction and real outcomes

Before executing the treatment action, the child predicted
`StructuralDelta(changed)`, learned with support 2 from its matching prior
transitions. After execution, R2 observed a changed active-binding signature
and reified the prediction.

| Branch | Executed action | Changed cells | Level before | Level after | Result |
|---|---:|---:|---:|---:|---|
| No spinoff | `ACTION_2` | 106 | 0 | 0 | baseline mistake; no progress |
| Context child | `ACTION_3` | 710 | 0 | 1 | prediction reified; level completed |

The treatment action also equals the action in the held-out recording, but the
held-out action and successor were not supplied to context discovery, child
construction, ranking, or prediction.

## Trace and interpretation

The measured trace contains the required sequence:

```text
ambiguity
→ context-discovered
→ schema-spinoff
→ action-ranking-changed
→ prediction
→ prospective-action
→ prediction-resolution
→ prospective-outcome
```

This is the shortest positive bridge requested: one bounded absence condition,
one child DAG, one graph edge, and a count-based rerank. It adds no production
planner, semantic label, option, model, or game branch.

The mechanism is generic enough to justify a **25-game diagnostic run**, since
candidate selection uses only schema arity/state, active bindings, and support.
It is not yet generic enough to justify promotion: this is one deliberately
selected deterministic transition, its structural prediction is coarse, and
the evaluation target was located from a known successful recording. A suite
run must therefore report opportunity rate, false spinoffs, and held-out action
and progress deltas rather than assume this case will transfer.

## Reproduce

```bash
PYTHONPATH=src /home/pauloabelha/reflector_old/.venv/bin/python \
  experiments/prospective-context-spinoff-control/run_experiment.py
```

Machine-readable evidence is in `summary.json`; the causal event sequence is
in `trace.json`.
