# Minimal explanation-driven control

## Scope

The first explanation layer is an episode-local control scaffold, not a new
schema language.  It reuses the current `SchemaGraph`, `Binding`, `Workspace`,
`TransitionCandidate`, and `Shadow` objects.  Reusable knowledge stays in the
schema graph; explanations and their scores are disposable episode state.

The operational loop is deliberately narrow:

```text
current Workspace bindings and activation
  -> bounded action-schema candidates
  -> episode-local Explanation assemblies
  -> ordinary transition-schema Shadows, projected before action
  -> inspectable action scores
  -> opaque ARC intervention
  -> ordinary Shadow confirmation/refutation
  -> explanation support update
```

## Reused R2 objects

- `SchemaGraph` remains the only symbolic store.  Existing generic
  `Domain`, `Codomain`, `Intervention`, `Before`, `After`, `Change`, and
  `Preserve` atoms in learned transition schemas provide the prospective
  vocabulary.
- `Binding` remains the situated realization record.  An explanation keeps
  references to current bindings; it does not copy or mutate schema bodies.
- `Workspace.activation` is the construction frontier.  Transition schemas
  are reached by ordinary `supports` links installed from the bounded set of
  predecessor-bound schemas when a transition is learned.  Explanation
  construction never scans the dormant schema store.
- `Shadow` is the prediction commitment.  A transition schema is partially
  grounded from the current observation and projected before intervention.
  The observed transition is then represented with the same R2 atoms and
  reconciled through `SHADOW -> REIFIED` or `SHADOW -> REFUTED`.
- Graph support, contradiction, projection success, and projection failure
  remain append-only evidence.  Explanation support is a transient view over
  those counters plus its own resolved commitments.

The committed context-spinoff experiments are not imported or duplicated.
They demonstrated that current bindings can condition action effects, but
their recording-specific runner is not part of this controller.

## Minimal `Explanation`

An explanation contains an episode identity, constituent schema IDs, current
binding references, unresolved schema-variable ports, provenance, projected
shadow IDs, accounted evidence, contradictions, and an inspectable score.  A
single transition schema is a legal explanation.  Compatible active bound
schemas may extend it, subject only to configurable beam and constituent caps;
there is no minimum constituent count at which an assembly acquires a new
semantic status.

Candidate seeds are active transition schemas whose opaque intervention token
matches a currently legal action.  Extensions may use only current bindings
connected to the seed by existing graph links.  Ranking is stable and capped
at `max_explanations` (default 8).

## Prediction and action ranking

For a compatible active transition schema, the controller grounds its domain
and any available `Before` values from the current R2 observation.  Codomain
and genuinely unknown successor values stay open.  Projecting that partial
binding creates an ordinary R2 shadow before the environment is stepped.  A
prediction signature is just the transition schema's existing `Change` and
`Preserve` atoms.

Observation-driven partial completions and final-boundary action commitments
have separate hard budgets.  The latter permits at most eight shadows per
decision cycle and at most sixteen open transition constraints per shadow;
this prevents a saturated sensory projection budget from silently disabling
control while preserving explicit boundedness in both paths.

For every legal opaque action the controller exposes:

```text
score = predicted_progress
      + discrimination_weight * explanation_disagreement
      - risk_weight * predicted_ineffectiveness_or_failure
      + support_weight * explanation_support
```

Progress and reward use only values returned by the ARC interaction
interface.  Disagreement is a transparent mean pairwise Jaccard distance over
the R2-native predicted effect atoms.  The local-schema ablation omits
multi-explanation support and disagreement.  Actions without a supported
prospective completion abstain and retain the seeded random ordering.

## Outcome reconciliation and firewalls

After the real action, the normally learned transition schema is grounded as
a transition-evidence batch.  A compatible projected schema reifies; a
materially different observed transition supplies positive contradictory
evidence for refutation.  Failed commitments are retained in provenance and
can retire an incoherent episode explanation without changing its reusable
schema constituents.

Game identity, level identity, coordinates, palette roles, and inferred action
semantics are excluded from construction and scoring.  Game ID is used only
by the ARC transport and trace provenance.  Complex-action coordinates remain
uniform samples made after the opaque action ID is selected.  No successor
data is available to construction or projection.

The experiment runner compares random, local-schema, and explanation policies
with matched game, seed, budget, perception, and schema learning.  It
parallelizes only independent games; each game trajectory remains sequential
and owns a fresh runtime.

## Running the controls

Run one harness policy directly with:

```bash
.venv/bin/reflector2-arc \
  --policy explanation \
  --game ar25 \
  --seed 0 \
  --max-transitions 30 \
  --max-explanations 8
```

Run the matched random/local-schema/explanation experiment with:

```bash
.venv/bin/reflector2-explanations \
  --game ar25 \
  --seed 0 \
  --max-transitions 30 \
  --workers 1 \
  --output-dir experiments/minimal-explanation-driven-control/rerun
```

The direct harness records `explanation-decision` before intervention and
`explanation-resolution` after the observed successor. The matched runner
keeps each policy in a fresh runtime and aggregates action changes, prospective
commitments, shadow outcomes, discrimination settlements, and progress after
changed actions.

## Current evidence and boundary

The preregistered experiment verdict is **CONTINUE-DIAGNOSTIC**. Explanations
formed in every game in the fixed 25-game cohort, made prospective
commitments, changed opaque actions, and reconciled predictions through normal
shadow reification/refutation. They produced no progress or completed levels
under the tested action budgets. The result therefore supports executable
situated explanation, not improved task control.

The measured missing bridge is:

```text
predicted transition consequence -> legally observed progress
```

The next experiment should freeze the explanation machinery and learn that
association from repeated evidence across distinct contexts. Action value must
flow through a prospectively predicted consequence that binds such an
association. Reward-label permutation and matched consequence/progress
permutation are required controls; deeper planning and domain roles remain out
of scope until prospective action-changing precision becomes positive.

Full measurements and traces are documented in
[`../experiments/minimal-explanation-driven-control/results.md`](../experiments/minimal-explanation-driven-control/results.md).
