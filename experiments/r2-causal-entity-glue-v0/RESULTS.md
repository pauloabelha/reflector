# Results

## IMPLEMENTED

The production CAE layer computes a structured causal-scope residual, induces
sparse common-transformation candidates, preserves primitive competitors,
requires two environment-cited settlements for support, tracks situated
identity independently of exact member binding IDs, refutes breakaway groups,
suppresses scene-wide common motion, exposes union geometry through
`SpatialEntity`, and reifies only supported candidates upstream of role
grounding and planning.

The generic suite covers all requested safeguards and interfaces in
`tests/test_causal_entity.py`.

## OBSERVED

Frozen Arcade run `run-1786496687295657139`, workspace
`generic_prospective--ar25--shared_live_qwen`, contains two consecutive
`ACTION_2` transitions over three content-addressed frames. In both
transitions, seven primitive regions translate by `(down 3, across 0)` while
preserving their pairwise layout. This agrees with the human-visible R2 trace.

For the dominant coherent transformation scope:

- changed primitive regions: 7;
- atomic actor explains: 1 region, 45 of 90 changed support cells;
- atomic causal coverage: 0.50;
- atomic unexplained regions: 6;
- retained CAE: 1 bounded seven-member factorization;
- CAE support settlements: 2, contradictions: 0;
- internal relation residual: 0.0;
- lifted causal coverage: 1.00;
- lifted unexplained regions: 0;
- last induction fitting time: about 3 ms in this run.

## INFERRED

The same frozen evidence changes the admissible actor granularity from one
45-cell primitive region to one supported seven-member causal entity. Generic
FIT can measure that entity's union occupancy and production role grounding
can retain it alongside primitives. The running Arcade worker predated this
code, so that divergence was not executed live.

## NOT DEMONSTRATED

- a live assembly-level successor prediction settlement;
- a ProspectPlanner route or first-command divergence;
- environment progress, level completion, or score improvement;
- arbitrary occlusion, fragmentation, merge, or split identity.

## Negative evidence and next experiment

Two additional boundary components change size by one cell as the board
content shifts. They do not share the seven-member translation signature and
are excluded from that coherent causal scope; this is evidence against simply
grouping every changed region. The strongest next experiment is a fresh
matched AR25 fork with CAE disabled/enabled from the same saved boundary,
persisting both `ControlProblem` values and settling the first assembly-level
prediction in the real environment.
