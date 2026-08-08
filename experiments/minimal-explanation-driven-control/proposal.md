# Proposal: Minimal Explanation-Driven Control

## Hypothesis

A bounded episode assembly of active Reflector-II transition schemas and
bindings can act as an executable local model.  Its prospective shadows and
their disagreement will change opaque action selection and sometimes improve
ARC progress relative to matched random and local-schema controls.

## Frozen mechanism

- Construct at most eight explanations from the current active frontier.
- Permit one-schema explanations; extend only through current `supports`
  connections and current `Binding` records.
- Derive predictions only from existing transition-schema `Change` and
  `Preserve` atoms.
- Project the selected action through ordinary R2 `Shadow` records before the
  successor exists.
- Rank with ARC progress, explanation support, predicted failure/ineffectivity,
  and pairwise effect-signature disagreement.
- Reconcile with the actual learned transition through ordinary reification or
  positive-evidence refutation.
- Keep action identities opaque and sample complex-action coordinates only
  after selecting an action ID.

## Matched controls

For every selected game and seed:

1. `random`: seeded uniform legal-action controller.
2. `local-schema`: active transition-schema ranking without competing
   explanation support or disagreement.
3. `explanation`: bounded assemblies, prospective shadow commitments, and
   disagreement value.

All three use the same ARC adapter, perception, runtime, transition learner,
environment seed, action budget, and schema-link indexing.  Each policy owns a
fresh isolated environment/runtime.  Game jobs may execute in separate
processes; the trajectory inside each policy/game remains chronological.

## Stages

1. Unit-level causal trace with two competing active schemas and a real R2
   reification/refutation settlement.
2. One to three public games to verify that explanations actually form and can
   affect the final selection boundary.
3. Fixed 25-game public cohort, `--workers 1` and parallel, requiring exact
   deterministic result equality.

The runner writes machine-readable results to `summary.json` and per-policy
human-inspectable JSONL traces under `runs/`.
