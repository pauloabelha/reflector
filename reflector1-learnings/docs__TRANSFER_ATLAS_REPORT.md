# Directed 20x20 transfer atlas

## Result

The exploratory atlas learned on each of 20 fresh synthetic levels and tested
the frozen result against every target level, producing 400 directed cells.
The run used four process workers with immutable cell inputs, deterministic
cell seeds, stable result ordering, and coordinator-only artifact writes.

| Measure | Result |
|---|---:|
| Cells solved | 398/400 (99.5%) |
| Zero-shot solves | 135/400 (33.75%) |
| Structural-probe solves | 155/400 (38.75%) |
| Accommodation solves | 108/400 (27.0%) |
| Unsolved | 2/400 (0.5%) |
| Mean squared action-efficiency score | 0.6192 |
| Mean transfer score | 0.5640 |
| Off-diagonal mean transfer score | 0.5615 |
| Prior-level regressions | 0 |

Completion alone overstates transfer: accommodation can recover a solution by
bounded search. The transfer score therefore multiplies completion by squared
two-action efficiency, reuse-phase credit, and structural-edit retention.
Zero-shot cells score 1.0 when optimal; structural probes average 0.5703;
accommodation averages only 0.0202 because it takes 7.70 actions and 537.4
complexity units on average.

## What the matrix teaches us

An additive variance decomposition of the 400 transfer scores attributes
21.9% to the learned source, 28.2% to target difficulty, and 49.9% to the
specific source-target interaction. The source Mind therefore matters, but no
single source representation dominates independently of its target. Analogy
correspondence is highly directional: the mean absolute difference between
`i -> j` and `j -> i` is 0.4092.

The paired A/B counterpart cells score 0.6274 on average versus 0.5582 for
other off-diagonal levels. Their zero-shot rates are 38.9% and 33.4%,
respectively. This is a real but modest matched-pair advantage; much of the
learned two-edge structure transfers across the whole procedural family.

Source quality varies sharply. The best source, L05, averages 0.8350 transfer
and 60% zero-shot; L09 averages 0.1547 and 10% zero-shot. Target receptivity is
even more extreme: L12 averages 0.9925, while L08 averages 0.0249. The hard
`extra_condition` target L10 causes both failures, including its own diagonal
cell. This falsifies the comforting assumption that learning on a level
guarantees efficient replay on that same rendered level under the current
grounding objective.

Control-level summaries reinforce the distinction. `combined_decoy` targets
average 0.8650 transfer, while `extra_condition` targets average 0.2972 and
95% completion. `reversed_relation` targets average 0.3194. The system handles
surface ambiguity much better than conditional or direction-changing causal
structure.

## Implication for the Kaggle goal

The experiment supports retaining version spaces, active probes, and
transactional accommodation. It does not support treating the current 99.5%
completion rate as competition readiness. The next algorithmic target is to
raise zero-shot/probe-efficient transfer while reducing the 27% of cells that
fall back to expensive accommodation. Specifically:

1. represent conditional preconditions and reversed causal orientation in the
   transported diagram rather than discovering them through action search;
2. learn which source schemas are reliable across targets and weight source
   selection before probing;
3. use expected information gain divided by action cost for probe selection;
4. compare against a source-free exploration baseline so transfer gain is
   causal rather than inferred only from the matrix;
5. repeat the atlas over genuinely different game families and then official
   ARC-AGI-3 development games.

## Artifacts

- `experiments/transfer_atlas/run-001/results.json`: all cell metrics and
  matrices;
- `experiments/transfer_atlas/run-001/cells.csv`: flat analysis table;
- `experiments/transfer_atlas/run-001/trace.json`: 9.2 MB canonical event
  stream;
- `experiments/transfer_atlas/run-001/report.md`: generated heatmaps.

Trace SHA-256:
`3487e0972554c580ee41fa2fe9ac58fa17699c948ce954d93768b5a27bd0a217`.

This is post-run exploratory analysis within one procedural synthetic family,
not a preregistered blind result or an official Kaggle score.
