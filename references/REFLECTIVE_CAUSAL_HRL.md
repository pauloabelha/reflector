# Reflective Causal Option Graph

## Proposed algorithm

Reflector should not become a standard hierarchical RL agent with symbolic
labels attached. The proposed algorithm, **Reflective Causal Option Graph
(RCOG)**, treats representational change itself as a credit-assignment target.
It learns both how to act and which distinctions, objects, relations, and
compositions deserve to exist in its policy language.

The central state is a belief over causal situations, not a frame hash:

```text
pixels
  -> objects, flow, persistence, controllability
  -> competing causal-state hypotheses
  -> parameterized schemes/options
  -> option-effect graph and bounded planner
  -> primitive action
  -> outcome evidence and structural credit
```

An option is:

```text
(initiation predicate,
 parameter binding,
 closed-loop policy,
 termination predicate,
 predicted symbolic effects,
 failure conditions,
 evidence ledger)
```

Options may accept objects, relations, goals, or other options as parameters.
This is the computational counterpart of immediately interpreting “carry the
mug as a drunk person”: a transport scheme is modulated by a gait scheme, and
their constraints are propagated to lower control without requiring a stored
macro for that exact request.

## What is new

Classical options learn temporal abstraction; MAXQ supplies value and state
abstraction; Option-Critic learns internal policies and termination; HAC and
HIRO repair nonstationarity between levels; modern skill work explains when
temporal abstractions improve exploration. None of these alone constructs a
new symbolic ontology and assigns causal credit to that construction.

RCOG adds five coupled operations:

1. **Assimilation** maps a transition into existing object and scheme
   vocabulary.
2. **Accommodation** splits or revises a causal state when predictions fail in
   a stable, intervention-relevant way.
3. **Reflecting abstraction** promotes a recurrent coordination among schemes
   into a parameterized higher-order option.
4. **Causal intervention credit** distinguishes a change caused by the chosen
   action from animation, timer, or correlated visual change.
5. **Epistemic selection** values experiments by expected reduction in
   decision-relevant uncertainty, not pixel surprise.

The hierarchy must earn its complexity. A candidate option is promoted only if
it compresses successful trajectories, predicts held-out termination effects,
and improves a paired planning or exploration ablation. Fixed macros that
merely enlarge the action space are rejected.

## Learning loop

For each primitive transition:

1. Compute discrete flow and object correspondences across frames.
2. Update competing causal-state hypotheses, including hidden phase and
   commitment variables.
3. Attribute observed changes to the primitive action, autonomous dynamics, or
   unresolved causes using targeted contrasts.
4. Update every active option with separate extrinsic, epistemic, and
   structural ledgers.
5. Relabel the high-level intended subgoal with the subgoal actually reached,
   following HIRO/HAC-style hindsight correction.
6. If progress occurred, propagate shortest symbolic distance-to-progress
   backward over evidenced transitions.
7. Propose bounded variations: parameter substitution, sequence, conditional
   composition, parallel modulation, inverse, symmetry transport, and
   termination refinement.
8. Promote only variations that pass compression, prediction, reachability,
   and counterfactual-ablation gates.

At decision time, plan over an option-effect graph. Unknown or low-confidence
edges request an epistemic option; known paths request an instrumental option.
Primitive execution remains closed-loop. If the world diverges from predicted
effects, terminate early, preserve the falsification, and replan.

## Necessary safeguards

- **Hidden trajectory is state.** A visually reversible probe is not reversible
  when the environment retains commitment, phase, life, or timer changes.
- **Subgoal testing.** An abstract child is not considered usable until a
  bounded test demonstrates that the lower layer can reach its initiation or
  termination region.
- **Off-policy correction.** When a lower scheme changes, reinterpret stored
  high-level transitions by their achieved symbolic effects.
- **Option invalidation.** New subgoals can change pass-through semantics; old
  option models must be revalidated.
- **No public-game oracle.** Official public IDs, routes, and solutions cannot
  seed runtime structures.
- **No LLM at inference.** An LLM may inspect bounded traces and mutate source
  between development runs, but the frozen candidate is purely symbolic.

## Development curriculum

Use ARC-Witness as a structural pretraining and falsification surface, not as a
proxy leaderboard. Hold out entire game families and mechanics; never split
random levels from the same generator across train and test. Measure zero-shot
transfer of object persistence, controllability, option composition, and
causal-state splitting.

Then use MiniHack for procedurally varied skill composition and Crafter/Craftax
for long-horizon resource dependencies. GVGAI is a later general-game test.
Procgen is useful for visual generalization but weakly diagnoses rule
acquisition. Official ARC public games remain evaluation and mutation targets,
not training data.

## First falsifiable milestones

1. On ARC-Witness family holdouts, an option graph must exceed primitive
   frontier search at the same action budget.
2. Removing the abstract planner must reduce transfer, proving hierarchy adds
   more than temporally persistent exploration.
3. Removing accommodation must increase causal-state aliasing on games with
   visually identical but history-dependent states.
4. Removing higher-order parameterization must hurt novel scheme composition
   while preserving primitive competence.
5. On the 25 ARC public games, RCOG must preserve v40's 16 levels and add a
   deterministic level under 10,000 total actions before promotion.

The quickest implementation path is not end-to-end value learning. First add a
research option ledger over existing symbolic traces, hindsight effect labels,
and the promotion tests. Only after those tests identify reusable abstractions
should option selection receive learned values.
