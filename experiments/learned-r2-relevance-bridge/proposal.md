# Proposal: Learned R2-Native Relevance Bridge

## Decisive question

Can Reflector-II learn reusable schemas of the form

```text
predicted structural consequence -> legally observed progress outcome
```

and use only successful structural bindings of those schemas to alter a
prospective action choice?

This experiment does not test planning, goals, skills, roles, action meaning,
or deeper explanation search. The three existing policies are imported from
the frozen explanation branch without source changes. The fourth policy wraps
the frozen explanation decision at the final selection boundary.

## Representation

One observed pair constructs an ordinary R2 candidate whose body is:

```text
Consequence(?c)
Effect(?c, <canonical Change/Preserve atom>) ...
ProgressOutcome(?c, negative|neutral|positive)
```

The effect atoms are exactly the consequences already emitted by the frozen
explanation engine. `?c` is a reusable carrier variable. No action, game,
level, coordinate, hand-authored object role, or successor feature occurs in
the schema. Progress sign is admitted only after the environment reports the
successor. The implementation calls these *relevance* schemas, not causal
schemas.

An observed alternative outcome adds contradiction evidence to an existing
schema with the same consequence. R2's existing support arrays, distinct
support contexts, schema state, shadows, reification, and refutation are used.
The experiment adds no schema language.

## Chronology and freeze

The input is two disjoint chronological JSONL streams:

1. a historical/public baseline learning stream containing genuine positive
   progress;
2. a held-out stream used only after the learned schema snapshot is frozen.

Every record represents an already completed transition. The runner rejects
an empty stream, duplicate or non-increasing sequence IDs, overlapping event
IDs, and a learning stream with no positive progress. It records a digest of
the exact ordered learning evidence and writes the immutable promoted schema
snapshot before optional live intervention.

At a live decision, the bridge receives only the frozen explanation engine's
prospective effect signatures and structural binding fingerprints. Outcome,
reward, successor, game ID, level ID, action history, and coordinates are not
arguments to matching or ranking. Held-out outcomes never update the frozen
snapshot.

## Promotion and confidence

A candidate is promoted only after at least two supporting observations from
two distinct contexts. A promoted schema carries value only when its smoothed
confidence

```text
(support + 1) / (support + contradictions + 2)
```

meets the frozen `2/3` threshold. One positive example cannot be promoted.
Positive matches add value, negative matches subtract value, and neutral
matches carry zero directional value while remaining explicit predictions.

Full consequence equality is not required. A promoted consequence may unify
with a subset of a larger predicted consequence. This is the deliberately
minimal mechanism for class-3 structural/compositional transfer.

## Frozen arms and final action gate

The arms are:

1. `random`;
2. `local-schema`;
3. `explanation`;
4. `explanation+learned-relevance`.

Arms 1–3 run through the existing `reflector2.arc_harness` and
`ExplanationEngine`. Arm 4 obtains the same frozen explanation ranking first.
Their exact source hashes and explanation-branch commit are preregistered in
`frozen-arms.json`; the runner aborts if any frozen implementation file differs.
The experiment delays only its prospective explanation commitment until the
final arm-4 action is known; ranking code and weights are unchanged.

Arm 4 executes a divergent action only when all of the following hold:

- its selected action differs from the frozen explanation selection;
- at least one promoted relevance schema is the reason for the difference;
- confidence meets the preregistered threshold;
- an ordinary R2 progress shadow is successfully projected and logged before
  the environment step;
- the successor supplies positive evidence that must reify or refute it.

If any condition fails, arm 4 executes the frozen explanation action. This is
an action-conservation diagnostic gate, not a solver heuristic.

## Nulls

Null A rotates progress labels within each trajectory, maximizing changed
labels while preserving the transition stream, opaque action sequence, label
marginal, and per-trajectory marginal.

Null B rotates consequence/binding pairs within each preregistered matched
context stratum, maximizing changed consequences while preserving record
order, progress frequency, trajectory metadata, and stratum structure.

Both null learners use the identical construction, promotion, confidence, and
held-out evaluation code. Their held-out outcomes remain true.

## Metrics and verdict

The primary live metric is exactly:

```text
positive progress after arm-4-only changed actions / arm-4-only changed actions
```

The machine report also includes bridge coverage, promoted schema count,
commitments, reifications/refutations, Brier score when defined, regressions,
game concentration, transfer classes 1/2/3, changes versus frozen explanation,
positive progress and completions after changes, null precision/calibration,
and exact support/contradiction event provenance for every value-bearing
match.

`PROMOTE` requires every gate in `preregistration.json`. Formation without
prospective behavioral advantage is `CONTINUE-DIAGNOSTIC`; ten or more changes
with no positive progress is `REJECT`. Offline deterministic replay is always
run. Live replay is explicit because it spends a second matched action cohort,
and promotion is impossible until it succeeds.

## Exclusions

The implementation contains no successor features, multi-step chains,
options, skills, goal schemas, semantic roles, Qwen assistance, rollout/tree
search, game priors, or manually authored progress meaning. Engineering code
is isolated in this experiment directory and cannot inject semantic truth into
the frozen Reflector-II runtime.
