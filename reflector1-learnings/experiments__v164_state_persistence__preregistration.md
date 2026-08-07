# Preregistration: v164 state persistence on official ARC-AGI-3 games

Status: **frozen before treatment execution**. Candidate:
`candidate-df8025bb91c33a59` (v164), action budget 400. This experiment may
instrument, serialize, reset, remove, or transplant existing state, but may not
change policy logic, add a heuristic/schema/search procedure, use a game ID in
action selection, or grant extra actions.

## Question and fixed panel

The estimands are the causal contribution of fixed engine priors/within-level
adaptation, cumulative within-game learning, reusable cross-game state, and
harmful or inert persistence. The fixed games are `lp85`, `ls20`, `tu93`, and
`sc25`; no substitution is permitted. The ordered transfer pairs are, in order,
`lp85 -> ls20`, `lp85 -> sc25`, `ls20 -> tu93`, `tu93 -> ls20`, and
`sc25 -> lp85`.

The environment root, versioned metadata, release artifacts, candidate config,
instrumentation, and this document are content-hashed by `frozen/manifest.json`.
Official local environments expose no seed parameter. Determinism is therefore
defined by a fresh `Arcade`/environment instance, byte-identical environment
files, the deterministic v164 policy, and identical action budget. No RNG is
introduced by the harness.

## Arms

- **L:** a new `SymbolicPolicy` from the same immutable `MindConfig` is installed
  immediately after completion of each nonfinal level, before the first action
  on the next level. The completion result is first learned and snapshotted by
  the outgoing policy; the new policy ingests the new level's initial frame
  without a predecessor action.
- **G:** one clean policy is retained across every level and retry of one game,
  then discarded.
- **A:** exact v164 lifecycle. The audit predicts A and G are operationally
  identical; both are nevertheless executed independently as a manipulation
  and replay check.
- **P:** the source G trajectory's preregistered reusable-state projection is
  serialized, loaded into a fresh target policy, and presented the target's
  clean initial observation.
- **R:** the identical source artifact is named in the run record but is not
  imported into the fresh target policy.
- **S:** import a different completed source G snapshot minimizing, in order,
  absolute schema-count difference, absolute canonical-byte-size difference,
  then lexical source game ID. If none exists at that point in the frozen run
  order, S is deferred until one exists; it is never synthesized.

The P transfer projection is fixed before results: the seven learned Mind stores
(`schemas`, `concepts`, `hypotheses`, structural credit, transformations,
comparisons, abstractions); content-addressed scheme/lifecycle/semantic outcome
stores; learned programs and relational/action-effect structures enumerated in
`EXPLORER_TRANSFER_FIELDS`; and sanitized retained phase-topology and pivot-goal
models. It excludes tracker scenes, observations, frames, trace, current state,
level index, environment objects, score, action history, visit graph, pending
actions, cursors, and episode-local plans. Import is rejected as contaminated if
the canonical transfer serialization contains a source game ID or a field name
designated as excluded.

## Fixed order and stopping

1. reset-boundary audit and clean-state serialization;
2. `lp85` L, G, A;
3. `ls20` L, G, A;
4. `lp85 -> ls20` P, R, S;
5. `lp85 -> sc25` P, R, S;
6. triggered schema ablations for either pair if target actions diverge;
7. `tu93` L, G, A; `ls20 -> tu93` and `tu93 -> ls20` P, R, S;
8. `sc25` L, G, A; `sc25 -> lp85` P, R, S.

Early stopping may omit later numbered blocks only if the execution environment
is unavailable or the frozen candidate fails replay. It may not stop merely
because an early result is null. Schema ablation is triggered by any difference
in target action ID/data at the same observation hash, or by any aggregate
completion, reached-level, action, or score difference.

## Schema-specific conditions

For every triggered pair, rerun the target with: full P; schemas removed while
other projected state remains; schemas only (no episodic state); schemas present
but invocation disabled through the harness; and a semantics-preserving stable
alias of transferred schema identifiers with any source-game token rejected.
No new schema is created. Because identifiers are content addresses in v164,
the alias map and all rewritten references must be saved and the pre/post schema
semantic payload hashes must match.

## Measurements and causal rules

Every run saves the action trajectory, observation hash, action/data/reason,
invoked scheme record/components,
level actions, score, completion, highest level, failures/resets, and serialized
transfer metadata. Every level saves canonical full/component state hashes,
byte size, schema count/IDs/hashes, and created/modified/deleted schema deltas.
Invoked schemas come from the operative record and component fields; rejected
schemas/options come from lifecycle validation/quarantine telemetry. No claim of
transfer is allowed without the first action/data divergence at an identical
target observation hash. Later observation differences are consequences, not
matched inputs.

Primary within-game contrasts are G-L, A-L, and A-G for completion, highest
level, actions, and score. Transfer contrasts are P-R; S-R diagnoses generic
extra-state effects. A result is replay-valid only if rerunning from the saved
state artifact produces the same observation/action prefix and aggregate result.

The verdict mapping is fixed: G>L with P≈R means within-game learning only;
P>R with schema ablation removing the gain means positive reusable schema
transfer; P<R means negative transfer; P≈R with differing internal state means
inert persistence; A≈L means effectively clean per level; A≈G means cumulative
within-game learning; all outcome arms alike means fixed priors or within-level
adaptation dominate. Equality means exact equality on completion, reached level,
and score, with action count reported separately; behavioral equality additionally
requires identical action/data trajectories under matched observations.
