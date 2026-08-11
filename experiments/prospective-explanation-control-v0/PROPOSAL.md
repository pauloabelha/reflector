# Prospective Explanation Control v0

## Frozen question and arms

Does one bounded forward consequence step through current situated explanations
improve real ARC action selection relative to the current explanation policy?

Arm A is the unmodified `ExplanationEngine.decide(mode="explanation")`
ranking, including its seeded-random fallback and stable action tie rules. Arm
B receives the same decision/beam and adds only an experiment-local closure:

```text
existing explanation effect signature
  -> compatible currently active transition signatures
  -> their preceding chronological progress/failure evidence
  -> prospective tuple ranking
```

The closure never constructs a raster, never learns, never changes a schema,
and has depth one. A prospective action can override A only when its consequence
tuple differs on progress, failure, robustness, or consequential
discrimination. Otherwise B explicitly records `prospective_abstain` and uses
A's action.

## Frozen consequence rule

For one explanation, a distinct active transition schema is a supported
consequence when its ordinary `Change`/`Preserve` signature is identical to the
explanation's predicted signature. Exact identity is deliberately conservative:
partial overlap cannot become evidence in v0. Historical progress and failure
come only from `ExplanationEngine` outcome statistics accumulated from earlier
real recording transitions. Failure is the sum of ineffective transitions,
regressions, graph prediction/projection failures, and contradictions.

For each opaque action the deterministic prospective tuple is:

```text
(P, -F, R, D)
```

where `P` is integer completed-level/progress support across distinct matching
schemas, `F` is integer failure support, `R` counts independently supported
explanations agreeing on a useful consequence, and `D` counts relevant effect
signatures that separate that action from another legal action. This lexical
ordering avoids unsupported floating coefficients. Remaining ties preserve
A's complete rank and then opaque action ID.

The beam is capped at 8, consequence matches at 16 per explanation, and total
explanation/consequence expansions at 128 per decision. Hitting a cap is traced.

## Frozen cohort selection

Selection uses only artifacts committed before this treatment run:

1. causal/control opportunity: first four lexicographic completed 25-game
   context-spinoff checkpoints with at least one eligible opportunity;
2. existing partial progress: first two lexicographic remaining public
   recordings with `max(levels_completed) > 0` and terminal state other than
   `WIN`;
3. negative control: first lexicographic remaining completed checkpoint with
   zero opportunities and recording `max(levels_completed) = 0`.

The frozen result is `ar25`, `cd82`, `sb26`, `sp80`, `cn04`, `g50t`, and
`ka59`; `ar25` is a sanity check, not a pass determinant.

## Chronology and matched execution

At packet `t`, both rankings see only the runtime after packet `t-1`. Packet
`t`'s recorded action, successor, and level delta are held out. After ranking,
equal actions are recorded without branch execution. A differing simple action
pair is executed from two freshly replayed environments; predecessor hashes
must match each other and the recording. Counterfactual successor processing
uses deep-copied runtimes and cannot update the chronological runtime. Complex
actions requiring payload synthesis abstain. Only afterward does the recorded
transition update the live runtime and explanation outcome history.

Each game is chronologically serial and owns one runtime. Games may run in
parallel processes. The run is capped at 40 packets and 8 executed overrides
per game, fixed before treatment execution.

For interruption safety, each game atomically checkpoints its isolated runtime,
controller, RNG, chronological cursor, and accumulated traces after every
packet. Completed-game checkpoints are additionally keyed by recording hash,
frozen configuration, and protocol version; reruns resume compatible work and
ignore stale state.

## Outcomes and verdict

Executed disagreements are classified by completed-level delta first, then by
treatment-only versus baseline-only correctness of the prospectively stated
structural consequence, else tie. Unavailable scores are reported unavailable.

`PROMISING`, `NEGATIVE`, and `INCONCLUSIVE` use exactly the thresholds in the
task specification. Prediction accuracy alone cannot yield `PROMISING`, and no
experiment code will be promoted into `src/reflector2`.
