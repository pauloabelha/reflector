# M8 causal object-world-model compiler

Date: 2026-07-30

## Purpose

The next major Reflector mechanism should compile a small causal world model
from rendered interventions, rather than add another game-shaped planner.
Its target is transfer across navigation, selection, coupled-object, and
multi-phase games.

The compiler may carry a generic operator grammar between games. It must not
carry game identity, literal colors, absolute coordinates, action IDs, routes,
or a public level's solved state.

## Missing capability

Reflector already has several strong narrow executors:

- exact finite connector assignment;
- relative lattice constraint solving;
- prospectively confirmed permutation transport;
- layered stencil construction.

The recurring failure is one level above those executors. The agent does not
yet reliably decide:

- which rendered changes belong to the task rather than a status layer;
- which persistent object or mode an action controls;
- whether a no-op means collision, wrong mode, wrong object, or an inert
  action;
- whether a visible receptacle, contact, arrangement, or reference match is
  actually the terminal predicate;
- when another actor or phase change makes a static plan invalid;
- which intervention best separates competing causal explanations.

These are world-model selection problems, not shortest-path problems.

## Contract

### 1. Typed latent state

Compile each frame into a bounded state with explicit roles:

```text
WorldState
  task_objects: persistent role-tracked objects
  nuisance_layers: counters, borders, cursors, and protocol feedback
  controllability: action family × object role × mode hypotheses
  relations: contact, containment, alignment, overlap, order, connectivity
  obstacles: static and dynamic occupancy hypotheses
  selectors: active-object, active-attribute, and phase hypotheses
  terminal_hypotheses: relational predicates awaiting progress evidence
```

Object identity is relational and transformation-aware. It may be conserved
through translation, recoloring, D4 transforms, partial occlusion, or a
learned local rewrite. Exact color counts alone are not identity.

### 2. Finite causal-program grammar

Every explanation is a typed program assembled from a small generic grammar:

```text
Select(role)
SetMode(role)
Translate(role, direction_or_relative_vector)
Transform(role, learned_local_operator)
Apply(role, target_relation)
Couple(role_a, role_b, relation)
Test(candidate_terminal_predicate)
```

A model binds rendered action tokens to these operators only through
intervention evidence. Bindings are episode-local and reset on every level.

Candidate models must explain:

- the changed task pixels;
- conserved and transformed object roles;
- unchanged relevant relations;
- nuisance-only effects separately;
- boundary-conditioned no-ops without treating unrelated side effects as
  collision evidence.

### 3. Version space and falsification

Maintain a bounded set of complete causal models, not one early guess.
Each selected action records its predicted successor partition before the
action is issued.

After observation:

- retain models that predicted the task-state transition;
- quarantine models contradicted by a causally relevant change;
- leave an action unbound when the observation is underidentified;
- never promote from the same transition that proposed a model;
- reset level-local authority after progress while retaining only grammar-level
  evidence and cumulative telemetry.

Reaching a candidate target without level progress falsifies that terminal
predicate. Visual plausibility never substitutes for environment progress.

### 4. Active causal experiments

When several models survive, choose an intervention by deterministic
worst-case hypothesis elimination:

```text
utility =
    guaranteed_model_eliminations
  + goal_hypothesis_eliminations
  + controllability_partition_gain
  - known_failure_risk
  - irreversible_resource_cost
```

Repeated action coverage has no intrinsic value. A probe is useful only when
surviving models predict observably different task-state outcomes.

### 5. Belief-state planning

Plan over `(world state, surviving causal models, surviving goal predicates)`.

- Execute a task action only when all authoritative models agree on its safe
  successor, or when it is the selected information probe.
- Replan after every observed transition.
- Include selection, mode, and phase in state.
- Treat other controllable actors as dynamic occupancy, not static scenery.
- Use exact bounded BFS/CSP/AO-style search after grounding; abstain on an
  incomplete model, exhausted bound, or unsafe disagreement.

## Knowledge-base priors

The offspring knowledge base may encode these falsifiable priors:

1. persistent compact objects are more likely causal units than status pixels;
2. local sparse transformations are preferred before global rewrites;
3. translation, recoloring, object order, and D4 transforms preserve operator
   roles unless contradicted;
4. selection, navigation, apply, and terminal checking are separable roles;
5. different action subsets may control different objects or modes;
6. a no-op is boundary/collision evidence only when task-state locality and
   controller family are identified;
7. goals are relational predicates and require actual progress confirmation;
8. useful plans may temporarily increase pixel disagreement;
9. exact bounded search is preferred after causal grounding;
10. ambiguity, cap exhaustion, and prospective conflict require abstention.

These priors rank hypotheses. They never override rendered evidence.

## Hard safety bounds

Initial bounds should be general symbolic budgets, independent of any watched
game:

| Quantity | Initial cap |
| --- | ---: |
| Task objects | 24 |
| Object-role hypotheses | 256 |
| Complete causal models | 512 |
| Terminal predicates | 128 |
| Stored prospective transitions | 256 |
| Belief-search states | 4,096 |
| Plan length | 64 |
| Controller assignments per action family | 120 |

Every exhausted bound produces a sticky per-level diagnostic and fail-closed
abstention. It must not raise through the runtime policy.

## Required trace

Each cognitive event must expose:

- task-object and nuisance-layer counts;
- active modes, selectors, and dynamic blockers;
- causal-model count and elimination reasons;
- controller and goal version-space sizes;
- selected probe and predicted outcome partition;
- prospective prediction, observed successor, and conflicts;
- search states, plan length, next agreed action, and abstention reason;
- level-authority resets and cumulative cross-level evidence;
- exact candidate ID and inference fingerprint.

The live dashboard should render the current model set, selected causal
program, goal hypotheses, predicted/actual transition, and planner frontier.

## Development and promotion protocol

`tu93` is the close-followed development game because it exposes navigation,
collision, controller induction, terminal falsification, and a later dynamic
blocker. Its literal topology or route is never eligible runtime knowledge.

The transfer set is:

- development: `tu93`;
- structurally adjacent: `ls20`, `ka59`, `dc22`, `wa30`;
- factored/multi-object: `tr87`, `sk48`, `sc25`;
- preservation: every currently accepted progress game.

Milestones:

1. **M8.1 — causal state compiler:** stable object/nuisance/role tracking and
   prospective transition explanations on at least four games.
2. **M8.2 — active model discrimination:** fewer actions than uniform
   exploration while identifying controllers or safely abstaining on at least
   three games.
3. **M8.3 — progress-grounded goals:** candidate terminals are confirmed or
   falsified without stale cross-level authority.
4. **M8.4 — belief-state execution:** new completed levels on at least two
   structurally different games, including one not used to tune the first
   implementation.

Promotion requires:

- exact-off equality when the M8 flag is disabled;
- no public game literals or watched-game bounds;
- prospective validation and deterministic target repeats;
- a cross-game gain, not only `tu93`;
- zero accepted completion regressions;
- full 25-game coverage;
- unit, metamorphic, adversarial, Ruff, mypy, export, and offline smoke gates.

## Falsifier

Reject or redesign the M8 branch if it merely reproduces a library of
game-specific detectors, if its model ranking cannot beat a uniform probe
control, if it reaches plausible terminals without learning from failed
progress, or if its only gain is the watched `tu93` route.
