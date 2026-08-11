# Eight-hour preregistered plan

## Objective

Within eight hours, produce one fully auditable same-state causal experiment
testing whether explanation-space search and bounded Python help QwenExecutor
choose a more informative or progressive ARC action, without violating R2's
epistemic or action-authority architecture.

## Scientific estimands

1. **B versus A:** effect of replacing the frozen PCW policy head with a
   dedicated verbal procedural context at the same state.
2. **C versus B:** effect of bounded code-mediated computation on the otherwise
   matched procedural context.
3. **C versus A:** pragmatic system comparison; this does not isolate Python.

A is never a competing live policy head in B/C. All three comparisons are
offline one-step branches from an identical prefix.

## Frozen battlefield-selection rule

Use the earliest decision in the admitted frozen PCW v1.16 `ar25` trace that:

1. has at least 24 committed predecessor transitions;
2. records `qwen_changed_action = true`;
3. records `decision.prior_used = true`;
4. records `prospective_plan.mode = control`; and
5. has an exact recorded one-step counterfactual branch.

This rule resolves to decision index 25 in the current frozen artifact. The
index is fixed before obtaining any new B/C response. Favorability is not a
selection criterion.

## Explanatory state

The decision snapshot carries two to eight live grounded explanations when the
workspace has them. Each explanation must retain:

- stable ID and claim;
- grounded bindings and evidence dependencies;
- support, contradictions, and explicit unknown/out-of-scope state;
- one-step predictions or prediction obligations;
- falsifying observations; and
- control relevance.

Semantic Qwen may create or criticize explanations but may not name a legal ARC
action. R2 may ground explanations and state discriminators but may not select
the next action. Executor alone binds an experiment to ranked legal primitives.

## Immutable decision snapshot

All arms must share a content-addressed identity envelope containing:

- source/build/config/model/seed/prefix hashes;
- current raw frame and authoritative observation record;
- all relevant predecessor transitions;
- exact action IDs and payloads;
- structured deltas and ordered animation summaries/references;
- live graph objects, bindings, explanations, evidence, contradictions, and
  provenance;
- R2 prospective predictions and hard constraints; and
- the legal primitive-action set.

B and C receive the same compact view and dependency aliases. C receives no
additional episode evidence through its tool.

## Executor output contract

Each arm emits ranked legal candidates. Every candidate includes:

- workspace/history dependencies;
- a computed reason and, in C, computation provenance;
- progress, decision-relevant information, option value, risk, and redundancy;
- an executable one-step successor checkpoint;
- an invalidation/stop condition; and
- one selected primitive action.

Abstention is allowed only with a typed, validator-consistent reason. In
particular, `NO_LEGAL_ACTION` is impossible when the snapshot has legal actions.

## Treatment compliance

For C to count as treated:

1. stage one selects Python mode;
2. nonempty bounded code executes successfully;
3. its structured return is durably recorded;
4. the selected candidate cites the computation and at least one returned
   finding; and
5. the action proposal is produced after that computation.

Failure of any item produces `INCONCLUSIVE_TREATMENT_NOT_ENGAGED`. C cannot
commit an action after Python failure in the decisive comparison.

## Executable checkpoint

A checkpoint is a conjunction of typed predicates over the real one-step
successor delta. v0 admits only generic observables already available from the
trace: grid changed, changed-cell count, changed bounding box, level-count
delta, terminal status, and exact entity/relation changes when represented by
stable workspace IDs. Each checkpoint carries a confidence in `[0, 1]`.

The frozen comparator records predicate accuracy, conjunction accuracy, and
Brier loss. Generated predictions never change empirical support; only the
environment-authored successor settles them.

## Action utility and authority

Executor may compute broadly, but it ranks actions under the qualitative rule:

```text
expected progress
+ decision-relevant explanation discrimination
+ option value
- risk
- redundancy
```

Hard safety/resource constraints are gates, not compensable score terms. Raw
disagreement is insufficient: it matters only when credible explanations make
different control-relevant predictions.

The arbiter checks legality, freshness, sole-source provenance, dependency
liveness, treatment compliance, proposal coherence, and checkpoint
executability. It never substitutes another action.

## Frozen controls

Before model calls or real branches, require deterministic fixtures for:

1. source, build, state, seed, prefix, prompt, and primitive-set identity;
2. semantic/R2/Executor/arbiter authority separation;
3. positive proposal and checkpoint comparison;
4. incoherent `NO_LEGAL_ACTION` rejection;
5. empty-history behavior;
6. coherent action/effect permutation equivariance;
7. insufficient/corrupted snapshot diagnosis;
8. Python success, timeout, parse failure, and runtime failure;
9. C treatment non-engagement;
10. positive, negative, and inconclusive verdict fixtures;
11. no-trigger deterministic routing; and
12. exact prefix and branch replay.

## Primary measurements

- branch progress and level-count delta;
- one-step checkpoint accuracy and Brier loss;
- explanations eliminated or reweighted;
- ambiguous bindings collapsed;
- risk, reversibility, and redundant-action avoidance;
- computation-to-proposal causal provenance;
- action, model-call, token, GPU/wall-time, and Python-runtime costs; and
- complete preregistered failure-funnel counts.

No single scalar silently decides the result. Hard failures dominate; progress,
prediction, and information outcomes are reported separately.

## Frozen verdicts

- **Positive C>B mechanism specimen:** treatment engaged; B and C share exact
  identity; C's computation causally changes its proposal; C has strictly
  better checkpoint loss and/or preregistered branch progress/information with
  no hard-risk regression.
- **Negative:** treatment engaged, identities and branches are valid, but C is
  neutral or worse on all target outcomes.
- **Inconclusive:** treatment absent, snapshot/state mismatch, invalid proposal,
  replay failure, comparator failure, deadline failure, or other broken causal
  precondition.

One positive development-game specimen proves mechanism plausibility, not
transfer. Promotion still requires a later frozen, sealed, mechanic-diverse
evaluation.

## Scope exclusions

No new game-semantic primitive, large ARC helper library, executable world
model, milestone planner, skill system, open-loop queue, cross-level tuning,
post-training, or model upgrade is admitted. Repeated missing generic operations
are logged as v1 candidates rather than added during v0.

## Eight-hour phases

| Elapsed | Phase | Exit evidence |
| --- | --- | --- |
| 0–1h | Audit and freeze | admitted sources, selection rule, dirty-tree isolation |
| 1–3h | Causal protocol | snapshot identity, coherent proposal, treatment gate, comparator |
| 3–4h | Qualification | all frozen fixtures produce expected verdicts |
| 4–5h | Battlefield | exact decision-25 prefix and A candidate materialized |
| 5–6.5h | Matched run | B/C calls and exact one-step branches preserved |
| 6.5–7.5h | Evaluation | frozen verdict plus mechanism/failure funnel |
| 7.5–8h | Finalization | hashes, replay, checkpoints, insights, results, reserve |

The global deadline reserves the final 30 minutes for durable finalization. If a
live call cannot finish before the reserve, the experiment stops and reports an
inconclusive result rather than losing its audit trail.
