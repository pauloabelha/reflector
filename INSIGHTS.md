# Reflector research insights and handoff

Last updated: 2026-07-29

This is the conceptual handoff for the next research agent. It complements,
but does not replace, `PLAN.md` (the authoritative continuation state) and
`REAL_GAMES_REPORT.md` (the authoritative score report). Read those two files
before acting.

## Executive truth

Reflector is an interesting but currently weak ARC-AGI-3 agent.

- Accepted agent: v49b, frozen inference commit
  `83287a7c2e508313fbb52b1982a921159823895e`.
- Local public-development score: **4.6401724704 / 100**.
- Progress: **19 / 183 levels across 10 / 25 games**.
- Fully completed games: **0 / 25**.
- Kaggle submissions: **0**.
- Kaggle public score: **not submitted**.
- Kaggle private score: **unavailable**.
- V49b is accepted. It conserves every v47b result and adds a learned
  higher-order operator over a reflected congruent object pair: ordered joint
  action effects, independently blocked topology planning, and a bounded
  continuation when planned contact temporarily merges the rendered objects.

The project has accumulated real causal mechanisms, but most gains are narrow,
one-level accommodations on known public games. The central unsolved problem
is not adding more symbolic vocabulary. It is learning the right causal state,
goal, and reusable operator from very few costly interventions, then executing
efficiently on a genuinely unseen game.

## Answer to the external research question

### Is there a strong set of symbolic, non-LLM ARC-AGI-3 agents?

Not on the evidence currently available.

There are useful non-LLM baselines, but no verified high-performing, purely
symbolic general agent on the current 2026 hidden Kaggle evaluation:

| System | Method | Evaluation | Result | What it proves |
| --- | --- | --- | --- | --- |
| StochasticGoose | CNN predicts whether an action or coordinate will change the frame; RL-style sampling | 2025 Preview, only 3 private games | 12.58%, 18 levels, 2 games, 255,964 actions | Learning affordances beats random exploration on that small preview. It is non-LLM, but it is neural rather than purely symbolic. |
| Blind Squirrel | Directed state graph plus pruning; a small ResNet18 ranks state-action pairs after progress | 2025 Preview, only 3 private games | 6.71%, 13 levels, 1 game, 109,108 actions | Graph memory plus learned milestone values is useful. It is a hybrid, not purely symbolic. |
| Explore It Till You Solve It | Training-free frame segmentation, salience-prioritized actions, directed transition graph, shortest paths to untested frontiers | 2025 Preview | Official submission: 3.64%, 12 levels, 0 games, 278,158 actions; paper reports stronger post-fix runs | A mostly symbolic graph explorer is a strong exploration baseline, but action cost is enormous and the evidence is not current hidden Kaggle transfer. |
| Reflector object/frame graph control v1 | Deterministic connected-object actions, conservative edge normalization, transition graph, shortest routes to untested frontiers | Paired 2026 local public suite, 400 actions/game | 0.0003283918/100, 1/183 levels, 0 games, 10,000 actions | Under Reflector's strict budget, a generic graph explorer collapses into visual-state explosion and nonstationary edges. This is the first apples-to-apples local control, not hidden evidence. |
| Duck | Coding-agent harness using Qwen 3.6 27B | 2026 ARC-AGI-3 Milestone #1 | Reported winner at 1.21% | Current hidden evaluation remains extremely hard, and the milestone winner is explicitly LLM-based. |

The 2025 Preview results are not comparable to the current competition. The
Preview evaluated three private games and allowed hundreds of thousands of
actions. The 2026 competition evaluates a separate set of 110 unseen games,
split equally between public and private leaderboards.

The correct conclusion is therefore:

> There is a promising family of graph-exploration and affordance-learning
> baselines, not an existing high-performing symbolic solution that Reflector
> can simply copy.

### Does Kaggle differentiate?

Kaggle differentiates agents by **hidden generalization, completion depth, and
action efficiency**, not by a separate symbolic-versus-LLM category.

The competition data page says:

- evaluation uses 110 unseen games;
- 55 determine the visible public leaderboard and 55 the final private
  leaderboard;
- per-level reward depends on human actions divided by agent actions and is
  squared;
- later levels receive greater weight in a game;
- the final score averages across games.

This produces four important separations:

1. Public-game specialization versus unseen-game transfer.
2. Public-leaderboard tuning versus private-leaderboard generalization.
3. Brute-force completion versus efficient learning and execution.
4. Solving an early level versus learning enough to progress deeply through a
   whole game.

There is no symbolic-only leaderboard visible in the official competition
materials. A non-LLM agent and an LLM agent are compared by the same score.
Eligibility, open-source, offline-runtime, and resource rules still need to be
checked against the live rules snapshot before any prize claim.

The current authoritative methodology specifies the upper-median human
baseline and a per-level cap of 1.15. Local reports should use that definition.
If a Kaggle page, cached notebook, or older Preview implementation disagrees,
record its version and evaluator hash rather than silently mixing score
definitions.

## The three deepest insights

### 1. The bottleneck is causal state construction, not search alone

Raw frames are not states. A single causal state can render differently because
of timers, animation, partial occlusion, autonomous replay, or other nuisance
variables. Conversely, the same stable-looking board can hide different
histories, commitments, phases, or controllable objects.

Reflector has observed both failure modes:

- On `g50t`, 184 raw frames collapse to roughly 14 stable board
  configurations after removing a monotone boundary countdown.
- The same visible board can still require a different future because a prior
  trajectory has been committed and may replay autonomously.
- On `ar25`, action meaning changes after a rendered marker-host relation
  changes.
- On `sb26`, a transient post-win frame looked like a new structural puzzle
  and generated a false hypothesis.
- On `sp80`, each life ended before a 32-intervention abstraction could mature.
  Resetting all epistemic state on `GAME_OVER` made the mechanism unreachable;
  conserving bounded same-level experience across retries recovered progress,
  while preserving the zero-failure parent path prevented regressions.

The needed representation is a bounded **belief/causal state**:

`objects + relations + phase + controllability + committed procedures + uncertainty`

It must be updated by interventions, not inferred from appearance alone. An
environment episode boundary is therefore not automatically an epistemic level
boundary.

### 2. Productive abstraction is executable compression with counterfactual credit

An abstraction is valuable only when it:

- predicts a transition not used to create it;
- reduces the number of interventions needed;
- composes into an executable policy;
- survives a relevant transformation or later level;
- and beats an exact-off, source-matched control.

Names such as “object,” “container,” “phase,” or “schema” do not themselves
constitute intelligence. V28 demonstrated this sharply: richer object,
enclosure, difference, and flow primitives added some progress but regressed an
accepted level and slowed other wins. Passive perception earned no task credit.

The strongest accepted mechanisms all compress observed causal regularities
into operators:

- a constraint becomes a repair action;
- a cyclic shift becomes transport;
- an enclosure link becomes recursive traversal;
- a translation becomes a goal-reducing motion operator;
- a marker-host reassignment becomes a phase variable that indexes action
  semantics.

### 3. Exploration must become hypothesis testing, then compilation

Pure graph exploration can find levels, but the squared efficiency penalty
makes massive search a poor final policy. Pure planning fails before mechanics
and goals are known. The right loop is:

1. **Explore:** choose the intervention that best discriminates current causal
   hypotheses.
2. **Verify:** repeat or contrast it only enough to identify a stable effect,
   precondition, goal relation, or falsification.
3. **Compile:** convert the evidence into a short parameterized operator or
   macro.
4. **Plan:** use the compiled operators, not raw trial and error.
5. **Reflect:** assign credit to the smallest structural change that predicted
   held-out evidence or progress.

The external graph-exploration results validate the first layer. Reflector's
accepted gains validate narrow cases of layers two through four. No existing
result yet demonstrates a general implementation of the complete loop.

## What the external systems teach us

### From StochasticGoose

Its target was deliberately modest: predict whether an action will change the
frame. It used a shared CNN backbone, hierarchical sampling of action then
coordinate, hash-deduplicated experience, and a model reset on new levels.

The lesson is not “replace symbols with a CNN.” It is:

- affordance prediction is a powerful exploration objective;
- coordinate actions need a spatially equivariant proposal mechanism;
- experiences should be deduplicated by causal equivalence;
- and a learned exploration policy can be simpler than a learned solver.

For a purely symbolic Reflector, the analogue is a calibrated, object-relative
affordance model:

`(object role, local relation, action role) -> probability and kind of change`

It should prioritize interventions but never pretend that “frame changed”
means “goal progress.”

### From Blind Squirrel

Its useful structure was graph memory plus backward credit from a newly reached
milestone. It pruned no-change and loop-producing actions, then learned values
over state-action pairs.

The important import is **retrospective distance-to-progress credit**. When a
level advances, back-label the causal path and train or update:

- which abstract states were on a productive path;
- which action roles shortened distance;
- which tests were merely epistemic;
- and which visual details were irrelevant.

Reflector currently attributes many local effects but does not yet propagate
progress credit cleanly through a causal trajectory at multiple time scales.

### From graph-based exploration

The strongest reusable baseline builds a directed graph of observed states and
transitions, prioritizes salient actions, and navigates by shortest path to an
untested state-action frontier. This validates Reflector's v14 direction.

The missing upgrades are:

- nuisance-normalized state keys;
- belief/history nodes when observations are non-Markov;
- explicit reset and irreversible-action costs;
- object-relative action proposals;
- a frontier score based on expected information and possible progress;
- shortest safe return to a frontier;
- and aggressive compilation once a transition family is known.

Do not copy its large action budget as a success criterion. In the Preview,
graph agents used roughly 100,000–278,000 actions over three games. That is
evidence of reachability, not human-like skill-acquisition efficiency.

## What Reflector has genuinely learned

These are narrow earned claims, not claims of general intelligence.

1. A state graph can causally outperform an equal-budget stateless control.
2. Perception should accommodate after falsification; unconditional ontology
   expansion can regress prior wins.
3. Local relations can be induced within a frame and retained across levels.
4. Overlapping constraints can coordinate repairs on a common lattice.
5. Successful action roles can be reused after stall, but reuse must be capped.
6. Rendered markers can ground coordinate-free goals and cyclic transports.
7. Conserved object motion can ground controller permutations and composed
   graph cycles.
8. An action scheme can take attributes and objects as parameters:
   select(attribute-bearing source), apply(target), commit.
9. Visual containment can parameterize bounded recursive execution:
   enter child, execute it, resume parent.
10. Appearance and alignment do not prove affordance. The failed v38 marker
    relocation was structurally elegant but causally false.
11. Frame differences can ground translation operators and shape-relative
    goals.
12. Action semantics can be conditional on an observable relational phase.
13. An abstraction layer must abstain during perceptual ambiguity if a
    lower-level, independently evidenced operator is active.
14. Parallel game evaluation must isolate processes; shared mutable state can
    invalidate scores.
15. Some controls are irreducibly joint: the correct causal state can be an
    ordered object pair, and one action can have coupled but independently
    blocked effects on its members.
16. Rendered object contact need not terminate a scheme. When contact was
    predicted by a grounded plan, a tightly capped latent continuation can
    preserve causal credit through temporary identity loss.
17. A local score, export, fixture, smoke test, and target-only run are all
    distinct from a Kaggle score.
18. Better local dynamics and deeper execution do not imply task
    understanding. V50 learned contextual pair transitions, v51 compressed
    them into a convergent transport family, and v52 granted exactly the
    preregistered post-accommodation plan depth. All three remained at one
    `m0r0` level. The missing variable was a terminal-relation/phase model, not
    another cap increase.
19. Inherited knowledge needs a causal scope, not just a content hash. V54
    initially renewed a per-level scheme budget on same-level death; v54a then
    revealed that generic grounding reattached an exhausted actionable scheme
    to later interventions. Both errors made the ledger look stronger than the
    policy actually was. Credit must name the definition, the intervention it
    selected, and the bounded interval during which it was causally active.
20. Relative symbolic priors create real diversity but are not common sense by
    themselves. Smallest-area changed `r11l` from 18 to 16 actions,
    rarest-shape solved it in 35, and largest-area lost the level. On the
    preregistered held-out click games, smallest and rarest exactly matched
    v49b and added nothing. A source-game efficiency gain is mutation evidence,
    not inheritance evidence.
21. A visually salient relation can be a reliable causal intermediate without
    being a goal. V55 grounded a sparse repeated field, planned both controlled
    objects onto it, and earned 54 exact distance reductions per retry. The
    last predicted step displaced the pair instead of advancing the level,
    producing five repeated falsifications and no task gain. Structural
    prediction credit and pragmatic goal credit must remain separate; the
    correct accommodation is to preserve the marker-triggered transport while
    retiring that grounded target from the terminal set.
22. Structural accommodation is useless if the planner cannot compose the
    conserved causal fact. V55a retired the first falsified marker binding and
    generated a different eleven-step assignment, but that route crossed the
    already observed transport trigger and reset. Goal search and transition
    learning cannot remain separate advisors: confirmed context-dependent
    edges must alter the successor function used to evaluate new goals.
23. Composing the right local models does not manufacture the missing
    objective. V55b made that integration operative: two portal edges were
    confirmed and consumed by marker-goal search, three distinct targets were
    falsified, and a sibling used the induced transport family throughout its
    search. Neither advanced. The next abstraction must explain progress over
    a sequence of phases or operations; accumulating locally correct
    transitions and trying more terminal bindings is not enough.

## What is still missing

### A compact causal object model

The agent needs object hypotheses with explicit uncertainty:

- persistence and identity probability;
- controllable, autonomous, goal, obstacle, marker, container, and nuisance
  roles;
- relative pose and topology;
- latent position during occlusion;
- and history-dependent mode.

Objects should be proposed cheaply from connected components, enclosures,
repeated shapes, motion coherence, and frame differences. Their roles must be
earned through interventions.

### A real action concept algebra

Humans can immediately understand “carry the mug as a drunk person” because one
scheme can parameterize another. The computational requirement is not arbitrary
symbol concatenation. It is typed modulation:

- procedure as an argument to another procedure;
- object/role binding;
- spatial or temporal transformation;
- prefix, suffix, interleaving, repetition, and conditional execution;
- constraint injection, such as wobble, avoid, alternate, or preserve;
- and downward compilation into primitive actions.

A useful type sketch is:

`Scheme[Object, Context] -> Trajectory`

with higher-order operators such as:

`modulate(base_scheme, variation_scheme, invariant_constraints) -> Scheme`

Every composition needs predicted intermediate states and component-specific
credit. Otherwise variation becomes undirected program explosion.

### Goal acquisition

Reflector is much better at discovering effects than discovering what counts as
success. Goal hypotheses should be explicit and ranked:

- match or overlap;
- fill or repair a violated relation;
- transport to a marker/receptacle;
- arrange by a demonstrated order;
- conserve a quantity while changing topology;
- activate/commit after construction;
- reproduce a shown example;
- or reach a stable terminal relation.

Evidence for a goal can come from invariant display regions, repeated level
structure, human-like visual asymmetry, progress transitions, and reversibility
tests. A hypothesis must predict a measurable potential function before it
controls repeated action.

### Partial observability and irreversible experimentation

The agent needs a belief graph rather than only a frame graph. A node should
include the observation equivalence class plus bounded latent variables such as
phase, committed macro, replay cursor, inventory, or control assignment.

Reversible-looking probes are not necessarily causally reversible. The active
v41 `g50t` work found that visual restoration after probing does not restore
the hidden committed trajectory. Online probes contaminated the later replay,
so the known 17-action development route did not reproduce when preceded by
apparently harmless exploration.

This is a major general lesson:

> Judge reversibility by future transition equivalence, not by the restored
> image.

### Credit assignment over structure

The desired Piaget–Drescher–Sutton–Barto–Popper synthesis is concrete:

- **Piaget:** assimilation applies an existing scheme; accommodation changes
  the scheme or representation when prediction fails; reflecting abstraction
  turns successful coordination into a new operator.
- **Drescher:** schemas explicitly represent context, action, result, and
  synthetic items; marginal attribution searches for causal relevance.
- **Sutton and Barto:** temporal-difference or return-based credit propagates
  sparse progress through the sequence of abstract states and operators.
- **Popper:** every promoted hypothesis includes a risky prediction and a
  falsifier.

What is missing is a unified update rule. A candidate structural mutation
should receive credit from three signals:

1. predictive improvement on later transitions;
2. information efficiency during exploration;
3. pragmatic return: level progress and action efficiency.

Complexity and regression costs must be subtracted. Credit should land on the
smallest changed dependency subgraph, not on every active symbol.

### Population-level variation without public-game monoculture

Parallel agents should differ in their meta-algorithms, not merely random seeds:

- graph-frontier explorer;
- object-affordance experimenter;
- relation/constraint inducer;
- macro and phase learner;
- topology/composition learner;
- conservative low-action agent;
- novelty-seeking broad explorer.

After each run, exchange only evidence-bearing artifacts:

- transition equivalence classes;
- falsified action/goal hypotheses;
- learned operators with preconditions and confidence;
- productive and wasteful causal paths;
- state abstractions and their collisions;
- score and action cost.

Breed offspring by recombining typed operators and mutation policies. Select on
held-out games, full-game depth, RHAE, and non-regression—not on whether a
specialist learned one public game. Keep one untouched validation partition and
rotate which public games are used for mutation pressure.

### A growing common-sense hash

The transferable unit should be an immutable, content-addressed
`SchemeDefinition`, not a mutable bag of confidence values and not an action
trace. Its canonical payload should contain:

- typed parameters and roles;
- preconditions over causal/belief state;
- predicted effects and invariants;
- a goal-potential contract, if the scheme claims pragmatic direction;
- dependencies on lower-level schemes by content hash;
- composition operators and bounded resource requirements;
- and explicit falsifiers.

Hash only that definition. Store support, counterexamples, calibration,
development partitions, action cost, and provenance in a separate append-only
evidence ledger keyed by the definition hash. This separation matters: two
agents can recognize that they mean the same operation even when they learned
it from different episodes, while bad evidence can be retracted without
silently changing the concept's identity.

The library root should be a Merkle hash over retained definitions and their
dependencies. An offspring inherits that exact root plus a mutation policy.
It may:

1. assimilate a definition unchanged;
2. accommodate the smallest falsified dependency, producing a new hash while
   preserving the parent and counterexample;
3. reflect a reliably coordinated subgraph into a higher-order definition;
4. compose definitions through typed role binding or procedure parameters;
5. retire a definition from selection without deleting its evidence.

There are three distinct inheritance channels:

- **ontogenetic:** within one episode, temporary beliefs and grounded bindings;
- **cultural:** evidence-bearing scheme definitions shared after isolated
  runs;
- **phylogenetic:** the offspring's exploration, representation, composition,
  and credit-update policies.

Conflating these channels creates leakage and brittle specialists. The
runtime candidate should contain the selected immutable library snapshot and
perform all episode grounding offline. Development may breed and select the
snapshot, but the exact accepted snapshot must be the Kaggle-exported one.

Promotion should use a structural return such as:

`predictive_gain + information_saved + pragmatic_return`
`- description_cost - regression_cost - calibration_error`

Credit lands on the smallest changed dependency subgraph. A definition that
only explains familiar public-game coordinates or routes receives no
inheritance credit. A definition that predicts a held-out transition family,
reduces interventions, or advances a held-out level does.

## Streaming agent “thoughts”

The useful stream is not unrestricted prose or hidden chain-of-thought. It is
structured, inspectable cognition:

- current causal state and uncertainty;
- active goal hypotheses and predicted potentials;
- proposed intervention and expected discriminating outcomes;
- observed result;
- prediction error;
- schema construction, accommodation, or falsification;
- advisor arbitration;
- selected action and reason;
- credit update;
- resource and action budget.

Reflector's cognitive JSONL already provides part of this. The next improvement
is to make every advisor expose:

`hypothesis -> predicted alternatives -> observation -> update -> action`

This lets an offline LLM or human diagnose the development run without placing
an LLM in Kaggle inference. The stream must remain bounded and derived from
operative state; fabricated narrative is worse than no trace.

## Starting schemas: useful or cheating?

A small set of content-free primitives is justified and probably necessary.
Humans also arrive with strong priors about objects, continuity, space,
causality, and goal-directed action. It defeats the purpose only when a schema
encodes a public game solution or arbitrary game-specific constant.

Good starter primitives:

- connected region, boundary, enclosure, hole, contact, overlap;
- normalized shape and repeated-shape equivalence;
- object persistence and split/merge hypotheses;
- frame difference and coherent discrete flow;
- translation, rotation, reflection, permutation;
- containment and support graphs;
- controllability and action-affordance probes;
- counters, clocks, animation, and nuisance hypotheses;
- select, apply, move, toggle, commit, reset;
- sequence, repeat, alternate, branch, recurse, and resume;
- conservation and monotone potential.

The discipline is to keep these as hypothesis generators. A primitive becomes
operative only after it explains interventions or constrains a successful
plan.

## Recommended research direction

The best next architecture is not a larger collection of game-specific
advisors. It is a **causal graph explorer that learns executable abstractions**.

### Layer 1: perception and state hypotheses

- Segment components, enclosures, repeated shapes, markers, differences, and
  coherent flows.
- Maintain multiple bounded identity/role hypotheses where ambiguous.
- Separate boundary clocks and animation only after action-independent
  evidence.
- Hash causal summaries, not full frames.

### Layer 2: epistemic intervention selection

- Maintain candidate action effects and goal hypotheses.
- Score actions by expected hypothesis discrimination, potential progress,
  reversibility risk, and action cost.
- Prioritize object-relative coordinates when complex actions are available.
- Use the graph to return by the shortest causally safe path to untested
  frontiers.

### Layer 3: operator induction

- Turn repeated transitions into typed operators with preconditions, effects,
  invariants, and confidence.
- Learn inverses only from future-transition equivalence, not visual reversal.
- Parameterize operators by object role, relation, direction, phase, and
  subprocedure.
- Preserve counterexamples.

### Layer 4: goal-conditioned planning

- Rank explicit goal hypotheses.
- Search over induced operators in belief state.
- Prefer plans that reduce a grounded potential and minimize actions.
- Re-plan after every surprising transition.

### Layer 5: reflecting abstraction and credit

- On progress, back-label the causal trajectory.
- Compress recurring coordinated operators into a new scheme.
- Compare the new scheme to its exact-off parent on source-matched runs.
- Retain it only if predictive or pragmatic utility pays its description cost.

### Layer 6: population evolution

- Run diverse meta-strategies across games in isolated processes.
- Share structured evidence after each level/run.
- Mutate representation, exploration, operator, and credit policies
  independently.
- Select on held-out generalization and action efficiency.

## Immediate experimental priorities

1. **Test whether paired-object abstraction transfers beyond `m0r0` level
   1.** Require the v49b grounding predicate to identify a qualifying pair and
   preregister joint-effect predictions before planning. Reject any widening
   that merely recognizes more pairs without improving prediction or progress.
2. **Reproduce an external graph baseline locally.** Port or adapt the
   open-source graph explorer as a separately configurable control. Compare at
   Reflector's exact 400-action budget and process isolation. This establishes
   whether Reflector's symbolic machinery beats a competent simple baseline.
3. **Add nuisance-normalized and history-augmented state keys.** Evaluate state
   collisions and state explosion on at least `g50t`, `ar25`, and a clean
   Markov game.
4. **Add retrospective progress credit.** After a level advance, propagate
   distance-to-progress labels through abstract state-action edges and measure
   whether later-level exploration becomes shorter.
5. **Build symbolic affordance ranking.** Predict frame/object/relation change,
   but separately model probability of goal progress. Compare with uniform
   frontier selection.
6. **Use human replays only as development diagnostics, not policies.** The
   public human dataset can reveal what information humans acquire early and
   which actions are wasteful. Do not encode replay routes or public game IDs.
7. **Make a real Kaggle submission.** Until Reflector crosses the hidden
   boundary, claims of generalization are speculation. Submit the exact
   accepted v49b export first as a baseline, if the user authorizes the external
   action and all live rules are satisfied.

## What the runtime-LLM probe actually established

The local hybrid experiment used Gemma 4 E2B with a symbolic scene summary,
frame difference, action candidates, and recent transition history. It
returned valid JSON for all 40 requests but made no `g50t` progress. Its
hypotheses remained generic, it selected no commit action, and five responses
described a different action meaning than the candidate actually selected.

This does not show that language models cannot help ARC. It shows that adding
a fluent policy head does not repair missing causal state, grounded operator
semantics, or structural credit. If an LLM is tested again, constrain it to
propose typed, falsifiable model mutations or goal hypotheses whose
predictions are checked by the symbolic core. Do not let free-form prose
directly choose actions and call that reflection.

The integrated follow-up sharpened this conclusion. Gemma was placed behind
the symbolic controller's explicit impasse detector, saw learned displacement
roles and gate failures, and its actual action received subsequent symbolic
credit. It still matched the symbolic control exactly on `g50t` at `[27, 53]`.
Twenty-seven consultations produced only five overrides, six invalid outputs,
and at least one action-name/candidate mismatch. The promising interface is
therefore not repeated action arbitration. It is a single typed proposal such
as “treat this gate as period-k,” with a bounded predicted observation,
symbolic compilation, and automatic retirement on falsification.

## What v41 established before rejection

The useful sequence was:

1. Greedy latent motion hallucinated progress through blocked edges.
2. Bounded A* used evidenced blocks but initially treated a paused autonomous
   object as replay divergence.
3. Pause-tolerant replay validated the saved four-step macro.
4. Preserving action effects and collision facts across deaths stopped total
   epistemic amnesia, but preserving one control choice caused repeated
   failure.
5. Independent first actions separated fresh and replaying objects.
6. Synchronous replay onset corrected a one-transition timing error.
7. Failure-driven macro-axis variation accumulated 21 collision facts, yet no
   level advanced.

The result supports a specific genetic-epistemology claim: accommodation
should modify the smallest falsified structure while conserving independently
supported knowledge. The agent did improve its internal model across retries.
But better internal diagnostics are not task success. The missing abstraction
is topology—regions, barriers, gates, and route homotopy—plus planning in a
belief state over which object is controlled and which trajectory is replaying.

## Decision rules for the next agent

- Do not call a target-only improvement generalization.
- Do not call evaluated games beaten games.
- Do not compare Preview scores directly with 2026 Kaggle scores.
- Do not call a CNN or ResNet agent purely symbolic.
- Do not infer a Kaggle score from local public games.
- Do not use raw level count without action count and evaluation surface.
- Do not promote an ontology because its traces look cognitively appealing.
- Do not infer affordance from appearance.
- Do not infer reversibility from visual restoration.
- Do not let a new abstraction interfere with an independently grounded
  lower-level operator during ambiguity.
- Do not accept an offspring without its exact-off source control, preservation
  gate, full 25-game run, tests, and exact Kaggle export.

## Primary sources

- [ARC-AGI-3 2026 competition](https://arcprize.org/competitions/2026/arc-agi-3)
- [Kaggle ARC-AGI-3 data and scoring](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data)
- [Kaggle ARC-AGI-3 leaderboard](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/leaderboard)
- [ARC-AGI-3 technical report](https://arxiv.org/abs/2603.24621)
- [ARC-AGI-3 human data and scoring update](https://arcprize.org/blog/arc-agi-3-human-dataset)
- [2025 Preview competition results](https://arcprize.org/blog/arc-agi-3-preview-30-day-learnings)
- [Tufa Labs Duck Milestone #1 write-up](https://tufalabs.ai/research/duck-harness/)
- [StochasticGoose source](https://github.com/DriesSmit/ARC3-solution)
- [Graph-Based Exploration paper](https://arxiv.org/abs/2512.24156)
- [Graph-Based Exploration source](https://github.com/dolphin-in-a-coma/arc-agi-3-just-explore)
