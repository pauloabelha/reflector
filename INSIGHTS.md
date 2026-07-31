# Reflector research insights and handoff

Last updated: 2026-07-31

This is the conceptual handoff for the next research agent. It complements,
but does not replace, `PLAN.md` (the authoritative continuation state) and
`REAL_GAMES_REPORT.md` (the authoritative score report). Read those two files
before acting.

## Executive truth

Reflector is an interesting but still weak ARC-AGI-3 agent.

- Accepted agent: v94b.
- Accepted candidate: `candidate-2d9cadd5859ce47d`.
- Local known-public-development score: **20.65827051873133 / 100**.
- Progress: **49 / 183 levels across the 25 public-development games**.
- Fully completed games: **3 / 25**.
- Total actions: **9,185**.
- Kaggle submissions: v65b `55113224` complete and v74 `55123277` pending.
- Kaggle public score: **0.02 for frozen v65b only**.
- Kaggle private score: **unavailable**.
- V94b is accepted. Relative to v92, only `ls20` changes; all 24 other
  score/action vectors are exactly preserved.

The project has accumulated real causal mechanisms, but most gains are narrow,
one-level accommodations on known public games. The central unsolved problem
is not adding more symbolic vocabulary. It is learning the right causal state,
goal, and reusable operator from very few costly interventions, then executing
efficiently on a genuinely unseen game.

## 2026-07-31 — v95: knowledge compression must remain prospective

The next useful abstraction is not another object type. It is conservation of
an already falsifiable causal algebra across level boundaries. In v94b,
`ls20` repeatedly presents the same 25-cell multicolor mover and the same four
five-cell translations, but clearing all knowledge on progress forces the
agent to relearn the primitive action category inside each short temporal
horizon.

V95 represents the previous level's complete algebra as a dormant scheme, not
as authority. One intervention in the new level must make a commuting square:
canonicalizing both movers up to color renaming yields the same partition, and
the concrete action yields the same abstract displacement. Only then are all
four laws transported. A mismatch destroys the entire inherited hypothesis
and the observed transition starts a fresh current-level model.

This gives “natural transformation” an operational meaning. Presentation can
change in layout and color vocabulary while the action/abstraction square must
commute. It also gives Piagetian conservation a safety condition: assimilation
is a compressed prediction tested against reality, and accommodation is the
smallest possible rollback. The HRL consequence is efficient reuse of
primitive operators without inheriting a route, goal, resource schedule, or
level solution.

The mechanism passes recolored-positive, noncommuting-negative, and
scene-discontinuity controls. The complete local gate is 501 passed and 3
skipped with Ruff and mypy clean. Accepted-trace replay locates a prospective
authority point in level 2 and predicts a behavior change; the fresh-process
target remains the required causal test.

## 2026-07-30 — v82f demonstrated analogy algebra accepted

The strongest post-restart gain came from treating `tr87` as a visible algebra
of examples rather than an interface to explore uniformly. A bounded parser
extracts framed glyphs, quotients masks by the eight symmetries of the square,
and compiles uniquely supported relations. Successive falsifications required
four increasingly general forms: class-to-class, class-to-sequence,
sequence-to-sequence, and composition through a latent bridge color.

The frozen agent reached 4/6 twice at `[56,45,44,38,217,0]`. Its full
process-isolated suite scored **16.355448098096414**, solved **39/183** levels,
and changed only `tr87` relative to v74. The full quality gate passed: 437
tests, 3 skips, Ruff, and mypy.

The earned insight is that visible examples can define a small relational
category: objects are dihedral equivalence classes, demonstrated mappings are
morphisms, variable-length outputs are products, and bridge-colored examples
support composition. This is substantially more useful than balancing action
types because it produces an executable prediction.

## 2026-07-30 — v83 track proximity rejected

V83 compiled and replayed only macros whose observed effect reduced a marker's
distance to a framed endpoint. On `sc25` the mechanism was operative but
remained 0/6 in 400 actions. The endpoint was part of the interface, not the
goal. This closes another undirected geometry branch: even a correctly learned
distance potential is useless when its target role is not evidenced.

## 2026-07-30 — v84 constellation alignment: first gain, broader form exposed

Black-box analysis of `re86` found that action 5 transfers control between
colored movers and actions 1–4 translate the selected mover on a three-pixel
lattice. In level 1, four colored landmark centers for each mover form a latent
plus target. The derived 20-action hand program completed the level exactly.

The first frozen autonomous offspring grounded all five roles without conflict
and completed level 1 in 34 actions, scoring 1.6243752403 on the target run.
It then abstained on level 2. That failure exposed the more general invariant:
the next scene contains a plus, an X, and a diamond, and each color has a set of
landmark centers that must lie on the corresponding translated shape mask.
Target inference is therefore translation subset embedding, not plus-center
intersection. Ambiguous pixel-level embeddings should be filtered by the
already grounded action lattice rather than by a shape-specific rule.

This is promising but not accepted evidence beyond one level. The stronger
parser must solve changed layouts reproducibly and pass preservation before it
can affect the canonical score.

## 2026-07-30 — v84b categorical option compiler: efficient but structurally false

The generic parser is now embedded in a common finite-domain control language
rather than another shape advisor. Relational states are objects; grounded
translations are endomorphisms; control transfer is a focus morphism; and an
action model is trusted only when concrete intervention and abstract
prediction form a commuting square. Landmark embeddings define finite CSP
domains. Bounded A* compiles a hierarchical option, and MDL-positive programs
are retained once rather than turning every successful suffix into permanent
knowledge.

This compression changed behavior reproducibly. Frozen v84b completed `re86`
level 1 in 24 actions twice, versus 34 for v84, raising the target score from
1.6243752403 to 2.7777777778. Each run accumulated 173 commuting confirmations
and zero commuting conflicts. The gain is real but narrow: level 2 still
consumed the remainder of the budget. Five actions were quarantined and the
last diagnosis was `constellation-structure-changed`.

The important disequilibrium is now sharper. The causal action algebra is not
being contradicted; the perceptual object changes under actions that should
preserve its constraint structure. Following Piaget and Drescher, the next
accommodation should weaken only that false synthetic-item invariant, using
the cognitive stream to determine whether mover masks, landmark groups,
selector identity, or clipping changes. Adding another task-specific planner
would conceal rather than resolve this contradiction.

V84c repaired the first contradiction by completing mover masks under central
symmetry: the diamond's apparently new pixel was merely revealed after moving
away from a crossing plus. The exact prefix then preserved its goal domain.
The full run exposed a deeper temporal issue. A moving diamond can overwrite a
landmark center and partially cover a stationary X, so a one-frame parser
assigns the wrong landmark color and shifts the X centroid. The appropriate
causal abstraction is therefore belief-state filtering: under a confirmed
translation, preserve constraints and every non-focused variable, and accept
only the predicted focused displacement. This is a naturality-based state
estimator, not permission to ignore an action contradiction; a mismatched
focused center still quarantines the morphism.

That state estimator supplied the sought behavioral leap. Frozen v84d solved
`re86` levels 1–2 in `[24,36]`, scoring 8.3333333333 on the target game. All
five controls survived with zero quarantines and zero causal conflicts, and
two MDL-retained programs were reused. This is the first evidence that the
categorical language is doing more than redescribing a specialist: a confirmed
morphism stabilized latent identity through observations that defeated the
one-frame parser, allowing the same CSP option compiler to solve a structurally
different level. Level 3 is still ungrounded, so the result remains
experimental until repeated and preserved.

Level 3 supplies another constructive accommodation: all movers share color 8
and overlap, so color-based variables collapse three causal factors into one.
Action 5 reveals focus anchors `(30,45)`, `(18,48)`, and `(45,48)`; one known
translation separates each factor's pixels despite overlap. Treating the scene
as a categorical product turns target inference into exact cover: choose one
reachable placement per factor whose landmark subsets are disjoint and
exhaustive. The unique minimum-cost solution assigns the line, X, and diamond
to `(27,6)`, `(42,24)`, and `(18,30)`. This is a genuine extension of the
common CSP language rather than a new route table.

V84e showed that offline CSP correctness is not enough: it learned the line
factor, restored it, switched focus, then lost the X selector when an upward
probe placed the marker directly on the same-colored line. The smallest safe
revision is temporal again. A marker may be absent only at its exactly
predicted destination when that cell has the mover color; the already known
inverse restore executes before any new focus inference. Any other absence
remains a probe conflict.

V84f passed that temporal test and solved level 3 in exactly 56 actions. The
result is strong mechanistic evidence: interventions separated three
overlapping same-colored factors, the exact-cover CSP assigned all eight
landmarks once, and the generic option compiler executed the assignments.
`re86` reached 3/8 with `[24,36,56]`, zero quarantines, and zero causal
conflicts. The product construction is therefore behaviorally validated once,
not merely plausible offline.

Level 4 removes palette equality as the binding shortcut. A clipped plus and
an X have colors 6 and 10, while their landmark constraints have colors 12 and
14. Completing the plus's symmetry outside the frame and solving all reachable
shape/group embeddings yields one bijection: `6→12` at `(15,30)` and `10→14`
at `(39,30)`. Committing both routes as one option is essential because the X
is recolored during its first movement. Persistent causal identity again
matters more than the latest rendered color.

V84g falsified the purely positional endpoint despite executing all 24 planned
actions. Interventions showed why: contact with a reference swatch repaints the
entire mover. A corrected black-box program painted plus `6→12` and X `10→14`
before embedding them, and moved away from the palette row before translating
sideways so the X did not cross the color-6 swatch. It solved level 4 in 44
actions. Planning must therefore include color in causal state and treat paint
acquisition/retention as option subgoals.

V84h turned that diagnosis into a bounded symbolic operator. Its A* state is
the product `(anchor,color)`; movement and paint contact are evidenced
morphisms; the terminal CSP requires both landmark embedding and the bound
reference color. The frozen agent solved level 4 in exactly the predicted 44
actions and reached 4/8 at `[24,36,56,44]`, target score 27.7777777778.
This is the clearest current example of useful accommodation and compression:
no route was retained as episodic prose, only a smaller causal state space and
an executable option over it. Level 5 is the next disequilibrium and should
first be tested as a composition or product of already earned morphisms.

That test exposed a coproduct as well as a product. The level-5 X and plus
jointly realize one color-9 target, while the diamond realizes a color-8
target. A one-mover/one-group bijection is therefore false. Two color-8
landmark centers also render as color 12 because the current plus lies over
them. Conserving the evidenced ring locations while making only those
causally overwritten center colors latent produces a unique joint CSP over
placement, paint state, and exact cover. Its assignments are X `(30,15)` and
plus `(33,51)`, both painted 9, plus diamond `(51,36)` painted 8.

A 63-action program compiled from those constraints solved level 5 through the
public wrapper. Conceptually, the natural transformation from concrete pixels
to landmark constraints must commute only modulo a justified occlusion map;
the target object is a coproduct of movers within a paint-color fiber. This is
also a useful MDL step: the agent needs one joint solver over already learned
morphisms, not three new shape-specific procedures.

V84i then supplied an HRL falsifier rather than a representational one. It
grounded all three options, but the paired-object advisor inserted five
primitive actions halfway through the plus route. The option later resumed and
reported its own goals satisfied, yet the world endpoint was wrong. A compiled
option is a semi-Markov action with an initiation set and termination
condition, not a loose suggestion queue. Arbitration must preserve that
atomicity unless a causal prediction fails or an action becomes unavailable.

V84j enforced that option boundary and solved level 5 autonomously in exactly
63 actions. The result is unusually clean: the manually predicted program
length, compiled program length, and observed level-transition length agree.
`re86` reached 5/8 at `[24,36,56,44,63]`, score 41.6666666667. This validates
the full chain from causal occlusion belief through coproduct/exact-cover
inference, paint-state planning, observed focus-cycle binding, and
semi-Markov execution.

Level 6 initially looked like a new deformation ontology, but conservation
compressed it. The 49-pixel plus is the product of two 25-pixel line factors
sharing one pixel and one action. Collision with a fixed obstacle can block
one line while the other translates, so the obstacle is a differential
actuator. The four plus landmarks require horizontal and vertical factors
whose centers differ by `(-9,+9)`. A sequence derived from obstacle width,
lattice step, and target line constraints creates that relative state.

The 72-pixel square likewise starts as a 19×19 perimeter and targets the four
corners of a 10×28 perimeter, also length 72. Obstacle contact transfers three
pixels of width into height per action. Composing these two factored options
solved level 6 in 57 public-wrapper actions. This is hierarchical planning in
a causal product configuration space, not a memorized deformation route.

V84k reproduced that 57-action consequence autonomously and reached 6/8 at
`[24,36,56,44,63,57]`, score 58.3333333333. Once again, predicted, compiled,
and observed option lengths agree. The gain supports a general strategy:
factor a conserved object until obstacle contact is deterministic on each
factor, plan in the product, and expose the resulting macro as one protected
hierarchical action.

Level 7 sharpens the abstraction. Interventions that translate one occluded
mover at a time reveal a 19×19 cross, a cross with 37-pixel horizontal and
19-pixel vertical factors, and a 13×13 loop. The target is most simply
described as a change of factorization rather than a change of shape: the long
horizontal and short vertical of the 37×19 cross shear within the color-8
fiber, while the two 19-pixel factors of the smaller cross shear within the
color-11 fiber. A first hypothesis that exchanged factors across the two
objects is rejected because its required relative offsets are outside the
reachable obstacle/boundary state space. Meanwhile, the loop's perimeter-48
invariant selects a 19×7 color-9 rectangle from two opposite-corner landmarks.
In categorical terms, obstacle-mediated factorization followed by paint
morphisms should commute with exact-cover recomposition while preserving each
object bundle. In Piaget/Drescher terms, the agent is assimilating a new scene
into existing translation, collision, paint, and conservation schemas; the
only accommodation needed is a factor-level relational state rather than
another game-shaped policy.

This factor-bundle model has produced a 32-action loop option and exposed a
crucial measurement hazard. Candidate 34/36-action asymmetric-cross routes
left original color-8 landmark centers visible, and a 45-action small-cross
route did the same at the isolated color-11 vertical point. Predicates that
inspected center color falsely called those states coverage. Continuous
factor-span reconstruction rejects all three. The trustworthy cross baselines
are 56 and 50 actions. Quotient search remains appropriate, but equivalence
must include causal occupancy, not merely rendered target color.

Composing the trustworthy routes finally produced the decisive causal test:
level 7 transitioned at total action 420. The 140-action within-level program
is outside the official budget, so it is diagnostic rather than a candidate,
but it proves that factor bundles, target bindings, paint fibers, loop
conservation, and protected option ordering jointly commute. The residual
failure is no longer semantic; it is a shortest-representative problem in the
same morphism class. Forty primitive actions must be removed before promotion.

Exact occupancy made aggressive compression safe. Coordinate descent over
macro counts removed 18 actions from the small cross without changing either
paint state or target spans. A coupled change—one fewer ascent and one fewer
descent—removed two from the loop, whereas neither count was independently
removable. The final `38 + 30 + 50 + 2 = 120` composition transitioned at
total action 400 exactly. This is a useful planning lesson: natural
transformations should be optimized over coupled commuting paths, because
locally indispensable primitives can cancel at the level of the composite.

V84l reproduced that exact composite autonomously: 7/8 levels,
`[24,36,56,44,63,57,120,0]`, and score 77.7777777778. The agreement among
black-box prediction, compiled option length, and observed transition is exact
for a third successive new level. The unchanged-suite projection is
19.4665592092, so this is a large validated abstraction gain but not yet the
20-point acceptance threshold.

An independent fresh-process rerun reproduced the exact vector, establishing
determinism twice. The remaining problem is now cross-game selection: acquire
at least 0.5334407908 aggregate points with the smallest independently
falsifiable extension, then run the full preservation gate.

`tr87` level 5 supplies a compact example of accommodation by dualization.
The earlier successful scheme read demonstrations and rewrote a flat answer
sequence. The new panel reverses those roles: two flat rows are fixed, while
the editable objects are alternating color-runs. Keeping the old direction as
an invariant made the panel look unrelated; preserving only the deeper
structure reveals the same analogy under a change of presentation.

Operationally, the run-length map
`(1→1),(1→2),(2→1),(1→1)` is a finite partition isomorphism. It transports
two length-five sequences into eight product-valued editable groups. Each
glyph is quotiented by the dihedral group before transport, so orientation is
nuisance while class identity remains causal. This compresses the target from
eight separately diagnosed goals into one partition plus two sequences and
reuses the previously learned selector/mutation controls unchanged. A derived
19-action public-wrapper program completed the real level. The general
compiler grounds the real frame uniquely and abstains on malformed partition
controls; autonomous evidence is the next falsifier.

The first autonomous v84m run passed that falsifier. It completed the grouped
level in 55 actions and reached `tr87` 5/6, without retaining the diagnostic
19-action string. The extra actions are the bounded cost of discovering and
traversing the mutation orbits prospectively; efficiency still saturates the
level cap. The result supports a useful HRL principle: transporting a learned
controller over an isomorphic object partition can preserve its causal
semantics even when primitive efficiency is not optimal.

An independent process reproduced the exact action vector. This matters more
than the nominal score: it shows the lifted controller is a deterministic
consequence of perception and retained causal operators, rather than a lucky
mutation-orbit traversal.

The 25-game preservation gate then measured **20.418940161588477 / 100**.
Exactly the two structurally targeted games changed; the other 23 retained
their complete score/action vectors. The result is the clearest evidence so
far that useful accommodation can be additive: a new presentation-level
functor reused the old causal controls while the factor-bundle hierarchy
remained behaviorally isolated elsewhere.

The next cross-game audit reveals a different compression opportunity. Across
the v84m suite, 43 progress events are advisor-homogeneous: successful levels
usually terminate inside a sustained specialist option. In contrast, all 75
failures are owned by generic exploration, and 73 follow one of two
four-action constant motifs. The important abstraction is not “repeat whatever
worked.” It is to quotient the successful state path by grounded action role,
run-length encode the quotient, and test whether the resulting option is
natural under the next level's perceptual re-grounding.

This separates Piagetian conservation from assimilation. The completed
level's concrete states are discarded; only a typed morphism word remains.
The next level supplies new objects and bindings. If the word cannot be
re-grounded, the agent abstains instead of forcing a route. If it can, exact
progress or contradiction supplies pragmatic credit. Failure avoidance is not
folded into the same mutation because progress transport and viability
learning have different falsifiers.

The v85 experiment falsified that proposed naturality. The role-compressed
word activated broadly and even improved `lp85`, but no game gained a level
and `ft09` regressed sharply when an old successful word was rebound into a
different phase. The 14-game mean fell from 36.4623931457 to 35.9812800045.
Syntactic transport of a morphism is therefore weaker than a natural
transformation: the required commuting square must include goal/phase
semantics, not merely matching action roles.

This negative result sharpens the next Piaget/Drescher move. Conserve the
supported causal operators, but accommodate a small viability predicate from
repeated terminal consequences. In hierarchical-RL terms, learn the initiation
set's unsafe boundary before learning another option policy. In CSP terms,
terminal edges become prospectively evidenced forbidden assignments. In
causal-learning terms, authority requires repeated consequences across
distinct concrete contexts, and specialist plans remain upstream of the
avoidance filter.

V86 then established that the domain of partiality must itself be compressed.
A whole-scene structural key was safe but too intensional: 65 terminal
hypotheses across all repeated-death games never matched a second distinct
source. A corrected game-local audit found that plain action identity is too
extensional and aliases thousands of safe transitions. The viable middle
object is an object-grounded action role. Five such edges were both repeatedly
terminal and free of safe aliases, and each recurred after prospective
confirmation.

Categorically, undefinedness belongs to the grounded morphism, not the entire
source object and not the untyped generator. In Drescher terms, the action plus
item-role context is the schema whose result may include terminal failure. In
HRL terms, this is an initiation-set exclusion for a grounded option. The
result is still only an offline hypothesis until an online role-local child
filters those edges without regressing accepted progress.

The online child completed that causal test. Four grounded roles earned
prospective terminal authority and seven candidate tokens were removed. Two
games changed their actual click sequences, yet no score, level vector, or
failure count changed. This falsifies “unsafe initiation-set learning alone
improves exploration.” It is constraint learning without a value function:
after removing one morphism, the policy selects another by undirected
fairness.

The next categorical object should therefore be a quotient transition system,
not a longer blacklist. A functor from concrete states to effect-equivalent
causal states is legitimate only when grounded action roles and their observed
outcomes commute under the quotient. Progress can then define a positive
potential on the abstract graph; terminal roles constrain its viable domain.
Piagetian accommodation changes the smallest failed equivalence class,
Drescher-style schemas provide action/context/result triples, CEGIS retains
competing subgoal predicates, and hierarchical planning compiles the selected
abstract path into a bounded option. This joins causal learning, CSP, and HRL
without pretending negative knowledge is itself a goal.

The first causal-quotient audit supplies unusually broad evidence compared
with prior local mechanisms. Compatible partial action/effect profiles made
458 prospective predictions across the full accepted suite and confirmed 422
of them. The 36 conflicts are not a reason to average outcomes; they are the
counterexamples that split an over-broad equivalence class. The quotient also
exposes 18,901 abstract frontier roles—actions untried in the current raw frame
but causally characterized in a compatible one.

This is the first post-v84 abstraction that simultaneously compresses many
games, makes falsifiable predictions, and defines a positive search direction.
It is not yet control evidence. The online trace-only child must reproduce
high precision with exact `ActionRole` and rendered effect typing before an
operative child may prioritize a novel predicted effect.

V88 completed that online test. Its exact grounded roles confirmed 285 of 308
prospective predictions across eight games (**92.53%**) while reproducing
every parent trajectory. The agreement with the independently computed
92.14% offline precision matters: the compression is not an artifact of a
post-hoc batch representation. It survives chronological, predict-before-
update execution.

The conflict rate also gives the control boundary. Partial bisimulation is not
an equivalence relation to assert globally; it is a defeasible local
simulation relation. Control authority should therefore be earned within the
current level, revoked by the first failed commuting square, and used only to
order already-legal generic interventions. This is a compact form of
Piagetian assimilation/accommodation and a cautious HRL initiation rule:
reuse a causal schema while it predicts, then split the abstraction at the
first disequilibrium.

The first control offspring then separated prediction from value. V89 used
only uniquely predicted positive structural effects and changed 22 decisions,
but gained no level or efficiency. On `ls20`, the reordered intervention
created the first quotient conflict in a previously 42/42 trace. This is the
right kind of accommodation—the controller revoked authority—but it also
falsifies the objective: “causes a component or relation to change” is not a
task potential.

The quotient should next serve epistemic action selection, where its semantics
are native. If compatible donor profiles disagree about an untried role, that
role is a CEGIS query: its observed outcome eliminates causal hypotheses and
refines the partition. Alternatively, completed trajectories can label
abstract states with distance-to-progress, but only if a chronological audit
shows the label transports under the quotient. These are respectively causal
identification and HRL value learning; neither should be conflated with a
generic preference for visible change.

The direct comparison now supports the epistemic branch. Across the frozen
chronology, ambiguous donor predictions define 878 query states and 1,672
candidate roles. All 135 queries the base trajectory happened to execute
eliminated hypotheses, removing 39.75% of the represented donor models. This
is stronger than a novelty heuristic: the action has a pre-observation,
model-relative information value and a post-observation eliminated set.

The progress-label control fails. A completed trajectory can assign a number
to an old state, but that number is not natural under a new level's goal.
Only one near-progress case aligned with the transported best role, versus 23
that did not. Thus v85's online regression and the new offline audit agree:
distance-to-an-old-terminal is not a transferable potential merely because
the local causal square commutes.

The resulting architecture is a finite scientific method. Compatible donor
profiles are competing causal models; their predicted outcomes form a
version space; expected model elimination ranks experiments; the observation
refines the partial partition. This is Drescher's synthetic schema
construction, Piagetian accommodation, CSP/CEGIS, and intrinsic-reward HRL in
one bounded operation. Its claim remains epistemic efficiency until a live
offspring improves task progress.

V90 confirms that the information metric is real online: 80 interventions
eliminated 46.17% of their represented causal hypotheses. It also confirms
that intrinsic information gain is not automatically useful under a fixed
400-action horizon. The refined profile currently changes only later
predictions; the generic controller still treats every raw frame/action pair
as new. No level or efficiency changed.

This suggests a sharper role for compression. A uniquely predicted
state/role outcome is not an epistemic frontier merely because the pixels are
new. If two compatible donors support the same effect, repeating it spends an
action to relearn an equivalence-class member. Ambiguous and unsupported roles
remain experiments; uniquely supported roles become redundant coverage unless
all legal choices are redundant. In category language, exploration should
cover morphisms of the quotient, not every concrete presentation. In HRL
language, this is state-action abstraction before option discovery.

V91 makes that compression operative at scale—7,201 concrete tokens omitted,
368 filtered decisions, and broader raw-state reach on three games—without one
new level. This is useful negative evidence. The bottleneck is no longer
ordinary exploration coverage. A policy can know which causal models disagree
and avoid relearning equivalent interventions, yet still explore the wrong
parts of a well-compressed world.

The hierarchy must now move from dynamics to telos. Progress supplies sparse
examples of terminal relational predicates; failures and no-ops supply
counterexamples. A bounded version space can propose predicates such as
contact, containment, alignment, equality of forms, completed permutation, or
phase synchronization without naming a game. Causal action effects can then
be evaluated by predicted reduction of predicate violations. This is where
CSP planning and HRL meet: the predicate defines an option termination
condition, and the causal quotient supplies its abstract transition model.

The `ls20` black-box solve supplies the missing positive example. The state is
not merely a frame or a causal-effect profile. It factors as a product:

- a rigid multicolor body's anchor in a 2-D configuration space;
- a symbolic 3×3 display phase;
- an invariant goal display;
- a small spatial operator whose exact overlap induces a phase morphism.

Navigation alone reaches the terminal chamber but is rejected while the phase
is wrong. Phase equality alone is insufficient until the body enters the
chamber. The successful procedure therefore composes two kinds of morphism:
spatial translations in the fiber and an operator-induced transition in the
base. This is a useful categorical picture—a finite fibration rather than one
flat state graph—and a concrete HRL picture: navigate-to-operator, apply,
navigate-to-terminal.

Piagetian accommodation appears at the right scale. The four translation laws
are conserved across the phase change; only the display-state factor changes.
Drescher's schema is
`operator-overlap + current-display -> next-display`. CSP planning searches
the product without replaying a public route. A synthetic gate must now prove
that the same compiler survives translation, recoloring, changed corridor
layout, and a different phase cycle before it receives live authority.

V92 now supplies the autonomous validation. After only rendered transition
evidence, the integrated agent compresses the scene into a rigid-body anchor,
four translation generators, two scale-equivalent display objects, and one
operator-induced phase morphism. It solves `ls20` level 1 in 17 actions twice,
shorter than the 19-action diagnostic route, because BFS discovers a different
valid representative of the same abstract option.

The categorical point is operational rather than decorative: spatial actions
are endomorphisms in the anchor fiber, operator contact maps between phase
objects, and display normalization makes the goal comparison invariant to
scale. The hierarchical policy is the composition
`navigate(operator) ; transform(phase) ; navigate(terminal)`. Piagetian
conservation is the rigid body and translation algebra; accommodation is
localized to the display factor when the operator changes it. The exact
14-game preservation gate shows that this compression remains dormant outside
its grounded conjunction.

Level 2 distinguishes a phase morphism from a contextual morphism. Entering
the visible operator can preserve the rigid body while teleporting its anchor,
rewriting the traversable topology, consuming a visible finite resource, and
changing the display. V93 correctly factors this composite and therefore no
longer mistakes the teleport displacement for a contradiction of a plain
action generator.

That better world model is still not a goal model. Equality can be transient
on the operator, and equality followed by teleport can latch a causal event
without making the fixed display host enterable. The official v93 run remains
1/7. The next Piagetian accommodation is therefore not another unconditional
option: maintain competing terminal predicates and eliminate them through
blocked-contact evidence. In categorical terms, observing a morphism into the
goal-display object does not prove that object is terminal in the task
category.

The next black-box intervention changes this interpretation. A thin component
decreases by a constant four cells per action; the alleged contextual
transition restores it to 84 while consuming a finite life. It is a horizon
reset, not a topology rewrite. The v93 latch therefore illustrates causal
confounding: operator contact and timeout occurred in the same transition.

Two hollow components share the budget component's color and act as spatial
resource morphisms. Contact resets the remaining horizon to 21 actions. This
effect explains why merely reaching them looked inert under a progress-only
predicate and why collecting them greedily failed: a reset collected too
early discards residual budget.

The verified 45-action level-2 solve is a resource-constrained natural
transformation between three representations:

- pixel area maps to remaining abstract time;
- normalized display succession maps to a phase object;
- shortest anchor paths map resource and terminal options into primitive
  actions.

The hierarchical CSP composes these morphisms as
`operator ; resource ; operator ; operator ; resource ; terminal`. Each
resource is scheduled at the latest feasible causal cut, so its restored
horizon serves downstream options rather than overwriting unused capacity.
This is Drescher-style schema construction with explicit preconditions and
results, Piagetian accommodation localized to the temporal factor, and
model-based HRL over a product of anchor, phase, remaining budget, and
resource availability.

## 2026-07-30 — clean restart and v75 translation algebra

A pinned fresh-process rerun from the v74 source commit exactly reproduced the
accepted 14.450686193334509 score and every per-game vector. A preliminary
non-isolated run through a shared editable environment did not reproduce v74;
that report was rejected because its source provenance resolved to a different
checkout. The practical lesson is that every subprocess must be pinned to the
frozen worktree, not merely passed the right candidate JSON.

Cross-game failure clustering then found the same missing abstraction across
multiple zero-progress games: stable relative translations recur while the
base graph treats nearly every rendered frame as a new state. The new bounded
compiler retains action identity plus relative displacement, requires a later
structurally distinct prospective confirmation, preserves contextual no-ops,
quarantines contradictory nonzero effects, and omits oversized substrate from
the task-object vocabulary.

On the clean v74 recordings, the inactive compiler forms prospective authority
on 13/25 games and same-episode inverse pairs on 7/25. `ls20` and `re86`
repeatedly yield complete four-direction algebras; `tu93` yields an inverse
pair; `dc22` yields only a partial algebra.

The compiler is now integrated behind one exact-off flag and emitted live
telemetry in a generation-35 trace-only offspring. Fresh isolated runs on
`dc22`, `ls20`, `re86`, and `tu93` exactly reproduced all four v74 action
vectors while gaining prospective authority on each game. This is real
representation and isolation evidence, not task progress. The next step must
construct a bounded relative-position quotient, then show better-than-uniform
probing or safe abstention before claiming useful control.

## 2026-07-30 — v76 generator-ray probe rejected

The first operative use of the algebra deliberately tested the simplest
explanation for the failure: perhaps uniform inverse-action alternation was
preventing spatial coverage. V76 therefore continued one authoritative
generator in a bounded straight ray, stopping on a contextual no-op,
conflict, progress, or a frame-derived cap.

That explanation was wrong. The probe displaced the base policy 198 times on
`dc22`, 320 on `ls20`, 305 on `re86`, and 8 on `tu93`, yet all four remained
at zero levels. Raw relative reachability is not the missing goal abstraction.
The next mechanism must condition on a relational event—contact, topology
change, phase change, or another prospectively evidenced discontinuity—or
abstain. Merely traversing a learned action group more aggressively is now a
closed branch.

## 2026-07-30 — v77 contact-affordance probe rejected

V77 tested the narrower idea that a prospectively predicted movement no-op is
an information-bearing contact event. It limited each authoritative generator
to one ray per episode and tried one least-used action outside the currently
known generator set at a novel relative contact signature.

All four preregistered games again remained at zero levels. The run also
revealed that “outside the known generator set” is not a stable affordance
type: while the algebra is partial, an ordinary but not-yet-authoritative
movement action can be mislabeled as a non-generator. Future action typing
must use positive effect evidence, not the complement of incomplete
knowledge.

## 2026-07-30 — v78 positive action-effect types

V78 replaces negative-complement action typing with a finite positive version
space. An action can gain a relative-translation, component birth/death,
form-change, relative-layout-change, or residual-change type only after a
later structurally distinct source confirms the preregistered kind. No-op
remains inapplicability evidence and never creates a type.

The clean-v74 audit yields authority on 17/25 games and non-translation
authority on 14/25. The crucial result is not just breadth but explicit
non-discrimination: live `re86` gives all five actions one shared type
signature, whereas `g50t` and `tu93` each expose two signatures. A six-game
fresh-process run exactly preserved every v74 action sequence, and `m0r0`
failed closed at the component cap. The next scheduler must consume only
positive distinctions and abstain when this quotient does not separate
actions.

## 2026-07-30 — v79 positive-effect fairness rejected

V79 waited for complete positive typing of represented plain actions and at
least two distinct signatures, then balanced a bounded number of trials across
effect families. This fixed the epistemic defect in V77: unknown actions were
never typed by complement, and `dc22` correctly abstained when all four typed
actions shared one signature.

The task result was still null on all seven preregistered games. Strong
operation on `cn04`, `ls20`, `sk48`, `tr87`, and `wa30` added no level.
Positive causal categories help describe the intervention space, but fairness
over categories remains undirected exploration. The next abstraction must
compose effects into an executable procedure or connect them to a learned
goal variable; another scheduling heuristic would repeat the same failure at
a different vocabulary level.

## 2026-07-30 — v68 accepted path-cycle result

V68 supplies a generic prior absent from v67: a conserved same-form
token-centroid domain may form one uniform simple rectilinear path, whose
contiguous intervals can support reversible cyclic transport. An otherwise
identical controller's identity may be grounded in local path topology rather
than appearance. On watched `lp85` level 5, this exposes a nested five-slot
subpath generator and a 21-slot whole-path generator. The controller form uses
endpoint/straight/corner context and normalized distance, never a game ID,
color, absolute coordinate, action ID, or stored route.

Two frozen repeats produce `[37,8,54,71,50,180,0,0]`. The eleven-game gate
and full 25-game suite change only `lp85`; the official local score becomes
`9.684019526667843`, with 28/183 levels, 11 games showing progress, two
complete games, and 9,486 actions. Cumulative cognitive diagnostics retain
31 confirmations and 27 plan steps through level progress. The level-5 delta
is 19 observations, 17 preregistered predictions, 13 confirmations, zero
conflicts, and 14 planned actions.

The evidence remains prospective rather than structurally held out. Both
initial promotions predict a later transition correctly, but each confirmer
grounds to the same physical controller centroid as its proposal. The gain
therefore supports topology-conditioned repeated effects and bounded planning
within one observed structure, not cross-controller or cross-game transfer.

The next frame is an important falsifier. Level 6 exposes 75 matching slots,
above the fixed 64-slot domain bound, so v68 reports
`domain-unrepresented`. The correct lesson is not to raise the bound until one
watched layout fits; any larger or branching transport mechanism must earn
separate evidence.

## 2026-07-30 — v67 accepted segmented-permutation result

V67 is frozen at
`509575e88cff60d33368006ca77b6eb30db67a40`, candidate
`candidate-a1ccbdb17d674b78`. It raises the local 25-game score from
`9.287893493473371` to `9.310463971112286` and levels from 26 to 27, while
preserving 11 games with progress, two complete games, and 9,486 total
actions.

The gain is localized to `lp85` level 4. V66 stalled after
`[37,8,54,301]`; two frozen v67 repeats both produce
`[37,8,54,71,230,0,0,0]`. A first segmented permutation stays provisional.
A subsequent same-form action must be preregistered and its full
conserved-token successor must match exactly before support reaches two.
Three represented effects then define a bounded permutation system; the
archived cognition stream shows exact BFS exploring 651 projected states
before its 13-step plan finishes level 4 at action 71. Every non-`lp85`
outcome is exact in both the eleven-game gate and full suite.

This evidence is prospective, not structurally held out: current v67 does not
require the confirming controller centroid to differ from the provisional
one. The frozen candidate rationale's “distinct equivalent controller”
wording overstates the runtime check. The exact current claim, archived trace,
and required distinct-controller follow-up are recorded in
`REAL_GAMES_REPORT.md`.

The abstraction is a reusable middle layer between observed dynamics and
search: controller forms exclude coordinates, colors, and action IDs; effect
laws retain episode-grounded slot permutations; and visible marker relations
define the projected goal. Ambiguity, prediction conflict, domain drift,
unsupported effects, or an unrepresented controller all abstain. The result
is still evidence on one known public game, not cross-game or hidden transfer.

## 2026-07-30 — v66 historical lattice-effect result

V66 is frozen at
`b6f9ba4476d19c3bea99acce1aa3a75c332e9678`, candidate
`candidate-c9825fedf72a2a32`. It raises the local 25-game score from
`7.973607779187656` to `9.287893493473371`, levels from 25 to 26, complete
games from one to two, and reduces total actions from 9,724 to 9,486.

The gain is causally localized. Two frozen `ft09` repeats both completed 6/6
levels at `[4,7,14,16,94,27]`, score `99.00375088921943`, and 162 actions.
Every non-`ft09` outcome in both the eleven-game gate and full suite is exact
relative to v65b.

One reporting lesson remains: the immutable target scorecards preserve all 11
lattice-planning decisions, but terminal level resets erase the earlier
lattice-grounding counters from `exploration_metrics`. Future runs should
aggregate mechanism counters across level boundaries. The reports also carry
the old generic `reflector-symbolic-v26` compatibility label, so exact
identity must continue to come from source commit, candidate fingerprint, and
artifact hashes.

The important abstraction is not “a solver for one board.” It is a three-step
symbolic procedure:

1. Ground one unambiguous regular lattice of repeated actuator forms and
   reuse only an already-earned local relation vocabulary.
2. Infer a binary relative click-effect law from at least two structurally
   different rendered interventions, then quarantine the law on any
   prospective mismatch.
3. Convert visible relation clues into an exact bounded CSP and execute only
   represented legal node actions.

The runtime does not contain a game ID, coordinate, color, action ID,
direction, or solution. Unknown clue symbols, mixed forms, ambiguous
groundings, same-context-only evidence, inconsistent effects, and planned
actions outside the represented frontier all abstain. This is still local
development evidence rather than proof of unseen transfer.

## 2026-07-30 — v65b accepted result and public-strategy reassessment

### Accepted local result

The accepted v65b source is frozen at
`ad68c9cd4c4915cbc220c25fba9998425ba5abd9`, with candidate identity
`candidate-34708ca0a3fb4129`.

| Measure | Accepted v64b | Accepted v65b | Change |
| --- | ---: | ---: | ---: |
| Local public25 RHAE / 100 | 4.640274445854323 | 7.973607779187656 | +3.333333333333333 |
| Levels completed | 20 / 183 | 25 / 183 | +5 |
| Games completed | 0 / 25 | 1 / 25 | +1 |
| Total actions | 10,000 | 9,724 | -276 |
| `sb26` | 3 / 8 levels | 8 / 8 levels in 124 actions | +5 levels and first full game |

The complete `sb26` result—**8 / 8 levels in 124 actions**—was reproduced in
two identical repeats. Every other game was preserved exactly relative to
v64b; the aggregate improvement is therefore causally localized to the
accepted `sb26` mechanism rather than offset by regressions elsewhere.

This is **local evidence on the 25 known public-development games**. It is not
a Kaggle public-leaderboard result, not a Kaggle private-leaderboard result,
and not evidence of transfer to unseen games. The frozen source and exact
preservation gate make it strong engineering evidence within that development
surface only.

### Progress across generations

![Reflector progress across all canonical evaluated checkpoints](reports/generation-progress.svg)

The trajectory is not a smooth story of accumulating score. Most accepted
mechanisms add one level at a time, and several apparently promising
experiments are correctly left as hollow, non-lineage points. V65b is the
largest absolute accepted-score jump so far: exhaustive structural closure,
uniqueness, and ambiguity abstention turned a three-level prefix into five
additional levels and the first complete game. The milestone boxes record
which general insight accompanied selected major gains; they do not claim that
version succession alone establishes causality. The chart contains every row
of the canonical score table in `REAL_GAMES_REPORT.md` and is generated by
[`scripts/generate_progress_plot.py`](scripts/generate_progress_plot.py).

The connector result reveals a broader architectural prior worth remembering:
when perception yields a small, finite, fully grounded problem, complete
enumeration with uniqueness is better than a plausible greedy repair.
Generalized carefully, the recurring disposition is to enumerate the bounded
operator or assignment space, require unique grounded identification where
the evidence supports that claim, and then search the resulting exact model
deterministically. V67's BFS returns a shortest goal path but does not prove
the path is unique. Exact modeling, bounded search, and abstention—not unique
execution plans in every mechanism—form the high-value K-line activation
bundle; the literal connector assignments are not.

### Public-strategy landscape and the proposal problem

The broader public-code and primary-literature review is recorded in
[PUBLIC_ARC3_STRATEGY_LANDSCAPE.md](references/PUBLIC_ARC3_STRATEGY_LANDSCAPE.md).
Its main conclusions are:

- Purely algorithmic ARC-AGI-3 agents exist, chiefly exact-frame or
  object-weighted graph explorers. No strong public peer was found that
  performs Reflector-like end-to-end pure-symbolic induction of semantic
  objects, affordances, transition laws, goals, and plans.
- Pure-symbolic object, DSL, planning, MDL, and causal-theory systems exist for
  static ARC and already-symbolized sequences. Their limited coverage shows
  that symbolic inference is bounded by the representational vocabulary and
  combinatorial search used to propose a theory.
- The strongest current public ARC-AGI-3 systems increasingly construct
  executable symbolic world models, replay observations exactly, and plan
  inside the certified model, but use an LLM to invent or revise the model.
  Their architecture supports Reflector's explicit-state, verification, and
  planning choices without demonstrating a pure-symbolic proposal mechanism.
- The central research problem is therefore **proposal**, not symbolic
  execution: construct the right perceptual parse, latent state, affordances,
  transition program, and goal predicate from very few costly interventions.

For Reflector, the pure-symbolic response is to maintain competing
representation and transition hypotheses, select interventions by expected
hypothesis elimination per action, use exact replay and counterexample-guided
synthesis, price model complexity explicitly, and anti-unify validated
programs into a held-out-tested symbolic library. V65b is a real gain, but it
does not by itself show that this general proposal problem has been solved.

## K-lines: associative priors for the proposal problem

The requested “K-lines” idea is Marvin Minsky's original memory proposal, not
merely k-nearest-neighbor search. A successful inference creates a K-line over
the useful agencies that were active; a later partial cue recreates a partial
problem-solving state. This maps unusually well onto Reflector.

The implementation decision is:

> content-addressed symbolic K-lines + exact sparse partial retrieval +
> bounded structural verification.

SHA-256 remains the identity and deduplication mechanism for an immutable
prior. A deterministic inverted index over canonical, typed cue atoms answers
which priors share part of the current symbolic state. IDF-weighted
containment produces at most 64 coarse candidates; exact relational
unification reranks at most 16; at most four registered generator dispositions
may be activated. Operation caps, not wall-clock limits, preserve replay.

Minsky's level-band principle supplies the central safety boundary. Recall
mid-level dispositions—an object vocabulary, transition hypothesis family,
informative experiment, or planner—not old pixels, literal actions, or the
claim that the current problem is already solved. A recalled K-line may reorder
probes; a structurally grounded one may prioritize hypothesis generation; only
a current-game-confirmed operator may enter planning. Similarity itself never
selects an action.

This is the missing retrieval layer for the existing content-addressed scheme
library. Definitions and evidence remain separately rooted; cue atoms are
translation-, recoloring-, object-order-, and action-role-invariant; canonical
tokens are verified after hash lookup; hidden evaluation cannot mutate the
frozen ancestral snapshot. The complete data contract, retrieval bounds,
tests, integration sequence, and primary sources are in
[KLINE_SYMBOLIC_MEMORY.md](references/KLINE_SYMBOLIC_MEMORY.md).

The first exact-off substrate now exists in
`reflector/core/kline_memory.py`. It content-addresses immutable definitions,
returns explicit registered generator dispositions from partial typed cues,
keeps evidence identities separate, verifies snapshot roots, enforces hard
posting/candidate/result caps, and never returns actions or code. Importantly,
even a complete cue overlap remains only **recalled** unless an explicit
current-state structural matcher grounds it. This implementation is isolated
from `MindConfig`, the explorer, policy, and Kaggle packaging; it therefore
changes neither v67 behavior nor its 9.310463971112286 score.

## `cd82`: colored-stencil composition, not a pose check

The public human trace resolves the main representation error. `cd82` contains
a reference grid, a construction grid, a selected palette attribute, and an
outlined template group that moves over eight relative poses. Applying the
dominant component overwrites a normalized cardinal or diagonal half-plane;
clicking a separate smaller outlined component overwrites its own radially
projected mask. The previously puzzling 12-cell effects are secondary
components, not clipping exceptions.

This suggests the compact language `SelectPalette`, `NavigatePose`,
`ApplyPrimaryTemplate`, and `ApplySecondaryTemplate`. Planning must use exact
last-write-wins composition rather than greedy pixel descent because useful
strokes may temporarily increase disagreement. The smallest safe experiment
learns primary masks from recolored prospective confirmations and targets only
levels 1–2. Secondary components and the still-ambiguous diagonal-boundary
terminal condition remain later gated stages. The complete grounding,
induction, planning, falsifier, and test design is in
[CD82_COLORED_STENCIL_DIAGNOSIS.md](references/CD82_COLORED_STENCIL_DIAGNOSIS.md).

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

As of 2026-07-30, stronger LLM/coding-agent results also exist, but they occupy
different evaluation surfaces. The ARC Prize community table reports
public-demo systems between 5.2% and 63.7%, and a later verified model report
gives Claude Opus 5 High 30.16% on ARC-AGI-3. OpenAI reports GPT-5.6 Sol at
7.78%. These are important upper alternatives to our architecture, not
like-for-like evidence for a symbolic learner or a Kaggle notebook. Separately,
the June Kaggle milestone winner was Duck, an offline Qwen 3.6 27B coding
agent. Public-demo saturation and hidden Kaggle performance must never be
merged into one ranking.

The public 25-game suite is itself a weak generalization test. A 2026 audit
reports that all 25 can be reached by simple forced or repeated actions, and
identifies a null-coordinate vulnerability affecting many games. Reflector
does not use that exploit, but its public-development score still measures
engineering progress on a known curriculum, not fluid intelligence.

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
24. A plausible procedure is not tested unless its event detector fires. V56
    represented pair disappearance and recovery as a confirmable option and
    compared three continuation policies, but all variants exactly matched the
    control and recorded zero procedure proposals. Direct parsing then showed
    that the visual diagnosis itself was wrong: both exact objects persist
    through a one-step discontinuous portal transition already represented by
    v50. Event abstraction therefore belongs below option learning, and event
    hypotheses must be extracted and preregistered from machine-readable
    recordings rather than inferred from a montage alone.
25. Cross-game common sense should begin with calibrated event prediction,
    not inherited goal stories. A content-free recording audit grouped exact
    repeated forms by shape and arity, conditioned their normalized effects on
    the selected action, and preregistered an expectation only after two
    matching observations. On the accepted `m0r0` recording it made 354
    supported predictions, confirmed 334, and exposed 20 real context changes,
    including the portal transitions that v56 had misdescribed. On five
    independently recorded held-out games it initially appeared to confirm
    987 of 987 supported predictions with zero deviations. V57 runtime traces
    then falsified the action representation behind that count: all coordinate
    clicks shared one action ID, so different object-relative clicks were
    incorrectly pooled. After grounding coordinate actions by their selected
    object role and abstaining on ungrounded coordinates, the held-out result
    is 913/913 confirmations with zero deviations; the alleged ten rare
    `lp85` affordance changes disappear. The event vocabulary remains
    predictive, but the correction is the deeper lesson: a causal event is
    defined jointly over state and a parameterized action role, never over an
    API action ID alone.
26. Confirmation is itself an intervention and must not recursively request
    confirmation. V57 `confirm-affordance` replayed 135 actions on `lp85` and
    fell from three levels to one; `confirm-discontinuity` replayed 338 and
    also fell to one, while losing `g50t` level 1. Two errors combined:
    coordinate-action conflation and a confirmation result being treated as a
    fresh surprise. The corrected mechanism structurally binds clicks and
    suppresses a second confirmation from the immediate contrastive replay.
27. Exact repetition is not a neutral confirmation when actions can toggle or
    consume state. V57a removed the recursive loop and restored all four
    control levels under `confirm-affordance`, but it delayed `lp85` level 2
    from 8 actions to 85. `confirm-discontinuity` still lost `g50t` level 1
    and one `lp85` level. The role-grounded `phase-segment` detector was
    operative but exactly matched control because raw frame digests already
    separated the affected states. A better accommodation is parameterized
    variation: after one member of a structural action role becomes newly
    effective, try an untested equivalent member rather than immediately
    repeating the same potentially reversible intervention.
28. Parameterized propagation needs causal scope just as confirmation does.
    V58 applied the intended role variation four times and preserved every
    control level, but one variation triggered the next, alternating between
    equivalent targets. It slowed `lp85` level 2 from 8 to 10 actions and
    supplied no score gain. An offspring action must not automatically become
    fresh evidence for producing another offspring. V58a therefore permits
    exactly one role variation per originating surprise and observes its result
    without recursively propagating it.
29. Noncascading is not enough; advisor priority expresses epistemology.
    V58a reduced the propagation to two independent actions but retained the
    same 8-to-10 action delay. Both actions interrupted an operative
    cyclic-alignment scheme. A newly reflected abstraction has less causal
    warrant than a repeatedly confirmed task procedure, so it must be offered
    only after grounded schemes abstain and before generic exploration. This is
    a concrete form of conserving lower-stage knowledge during accommodation.
30. Absolute deference makes reflection safe but inert. V58b restored the
    exact control trajectories, yet 62 maximum in-level detections produced
    zero variations because a grounded advisor always selected first.
    Reflection needs a conditional right to interrupt: conserve the current
    scheme while it progresses, then permit a bounded structural mutation only
    under pragmatic disequilibrium. This is closer to Piagetian accommodation
    than either unconditional preemption or permanent subordination.
31. Disequilibrium gating can correctly reject an abstraction. In v59 the
    three newly-affordant `lp85` events occurred at only 4–6 consecutive
    no-progress steps while cyclic alignment was still working. The level
    advanced before the eight-step disequilibrium threshold, clearing the
    pending variations. No corresponding event appeared on the genuinely
    stalled later level. Exact control behavior was preserved, but zero
    variations were selected. The correct conclusion is not to lower the
    threshold until something fires; this event family is useful predictive
    common sense but is not the missing procedure for these stalls.
32. Predictive inheritance and policy inheritance need different gates.
    Requiring level progress for every definition discards calibrated world
    knowledge; allowing prediction alone to select actions repeats v57's
    mistake. The first cross-offspring common-sense snapshot therefore admits
    `stable-repeated-form-action-effect` as an observation-only definition:
    2,047 confirmations, 20 counterexamples, 1,713 held-out confirmations,
    three agent provenances, and 0.9676% prediction error. Its cultural root is
    `b342e83f2bb14b134f8febf1b203c208ee74193b0bf0d07bc3796fc8df329a78`.
    It carries zero progress credit and cannot enter action attribution or
    selection until a separate runtime mutation earns pragmatic evidence.
33. The first cultural offspring preserves behavior exactly. V60 embeds the
    definition root, evidence-ledger root, and combined common-sense root in
    its genome. Against a current-source exact-off sibling on `ar25`, `g50t`,
    `lp85`, `m0r0`, and `sb26`, both scored 8.6109922903, solved the same ten
    levels, and had identical per-level action vectors. V60 exposed one
    inherited definition and selected it zero times. The exact candidate also
    exported and passed the network-disabled Kaggle smoke test. This proves
    faithful cultural transmission without behavioral leakage; it does not
    prove task improvement.

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

The library should be trained as a population-level continual-learning system,
not by letting one runtime mutate a shared dictionary:

1. Run isolated agents on disjoint curriculum games and emit immutable
   definition proposals plus append-only evidence.
2. Canonicalize proposals by typed semantic equivalence, not by their learned
   names, colors, coordinates, or action IDs.
3. Replay each proposal on recordings it did not create and score held-out
   prediction, intervention savings, calibration, and false activation.
4. Admit only definitions that clear a minimum-description-length and
   held-out-utility threshold; preserve counterexamples beside support.
5. Breed offspring from a frozen Merkle root while mutating selection,
   exploration, composition, and structural-credit policies independently.
6. Evaluate offspring on rotating game folds, then on one untouched lockbox
   fold. Never write lockbox outcomes back into the generation being selected.

This is the defensible form of a growing “common sense hash”: cumulative
executable causal knowledge with versioned evidence and population selection.
It is not a cache of successful routes. The first training target should be
cross-game event and affordance prediction; only later should the system
inherit goal claims, because Reflector's evidence shows that effect learning
is currently much better calibrated than goal acquisition.

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

The external graph baseline, nuisance-reduced component frontier, paired-object
experiments, connector synthesis, and lattice-effect experiment have now been
run; v64b through v68 incorporate their accepted consequences. The active
priorities are:

1. **Keep `lp85` level 6 as a distinct hypothesis boundary.** Its 75
   same-form slots exceed v68's fixed 64-slot domain bound. Require new
   intervention evidence and preservation before changing that bound or
   introducing a larger/branching transport model; do not encode the watched
   route.
2. **Integrate K-line recall exact-off.** The standalone content-addressed
   index is built and adversarially tested. Next bind its immutable index root
   into `MindConfig`, compile cues only from existing symbolic state, and
   measure held-out retrieval before it may reorder generators.
3. **Test colored-stencil composition on `cd82`.** Public replay evidence
   supports a unique reference, palette, construction canvas, outlined
   template group, eight-pose perimeter graph, primary half-plane overwrites,
   and separate secondary outlined components. Start with recolored
   prospective confirmation of primary masks and require 2/6 within 80
   actions; do not add secondary components or the narrow diagonal-boundary
   goal fallback before that gate. See
   `references/CD82_COLORED_STENCIL_DIAGNOSIS.md`.
4. **Maintain competing causal hypotheses and choose discriminating probes.**
   Add an explicit version-space/CEGIS experiment on one target before
   widening the shared policy. Count eliminated hypotheses per action and
   preserve no-op evidence.
5. **Add retrospective progress credit.** After a level advance, propagate
   distance-to-progress labels through abstract state-action edges and test
   whether later-level exploration becomes shorter without contaminating the
   frozen runtime with public routes.
6. **Use human replays only as development diagnostics, not policies.** The
   public human dataset can reveal what information humans acquire early and
   which actions are wasteful. Do not encode replay routes or public game IDs.
7. **Monitor v65b and submit v68 deliberately.** Submission `55113224` remains
   a pending v65b hidden-transfer calibration; v68 is technically ready but
   not submitted. Preserve the exact candidate/notebook mapping described in
   `references/KAGGLE_ARC3_SUBMISSION.md`. Until Kaggle returns a result,
   public and private leaderboard scores remain absent.

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
- [ARC Prize Milestone #1 results](https://arcprize.org/blog/arc-prize-2026-milestone-1)
- [ARC Prize community leaderboard](https://arcprize.org/leaderboard/community)
- [Claude Opus 5 ARC-AGI results](https://arcprize.org/results/anthropic-claude-opus-5)
- [GPT-5.6 model results](https://openai.com/index/gpt-5-6/)
- [Explore Before You Solve benchmark audit](https://arxiv.org/abs/2605.25931)
- [StochasticGoose source](https://github.com/DriesSmit/ARC3-solution)
- [Graph-Based Exploration paper](https://arxiv.org/abs/2512.24156)
- [Graph-Based Exploration source](https://github.com/dolphin-in-a-coma/arc-agi-3-just-explore)
## 2026-07-31: receding-horizon resource choices require option atomicity

V94 compiles the black-box temporal diagnosis into a general product state:
body anchor, normalized display phase, inferred remaining action budget, and
bounded same-role reset resources. The meter and reset relation survive
recoloring and layout changes in synthetic tests. On the verified legal
recording, the planner matches every one of the final 26 actions once its four
primitive translation morphisms are grounded.

The first autonomous isolated run remains at one `ls20` level. Its most useful
trace is the second retry: the agent infers a four-cell action cost, a
21-action capacity, and two resource candidates; it selects a reset path, but
ordinary one-step replanning abandons that target before contact. It later
reaches display equality with insufficient budget and times out. Thus the
causal model was adequate while the hierarchical execution semantics were
not.

The minimal accommodation is Sutton-style option persistence expressed in
Reflector's symbolic terms: after initiation, preserve the selected resource
object and its compiled path until the reset postcondition is observed or a
path/role falsifier fires. This is also the categorical coherence condition:
primitive path arrows must compose to the chosen reset morphism rather than
being reselected independently at every intermediate object.

## 2026-07-31: atomic reset options produce the autonomous second-level gain

V94b changes only the termination semantics of the temporal-resource option:
once a reset role is selected, primitive translations continue to compose
toward that object until reset evidence or an explicit falsifier terminates
the option. In a source-frozen fresh process this advances `ls20` from the
accepted 1/7 to 2/7 at `[17,240,143,0,0,0,0]`.

This is a sharp causal result. V94 already perceived the four-cell action cost,
21-action horizon, resource roles, operator phases, and terminal relation, but
remained at 1/7. Preserving the selected option—without a new color,
coordinate, route, horizon constant, or game identifier—was sufficient for
the extra level. The Piagetian accommodation modified the smallest falsified
scheme; the categorical reading is associativity of the compiled primitive
path with its intended reset morphism; the HRL reading is option atomicity.

An exact second fresh-process run reproduces the score, four resets, and every
level-action count. The result is therefore not a one-run exploration
accident; target repeatability is established before wider preservation.

The accepted-win preservation gate then isolates the effect across 15 games:
all fourteen non-target vectors are exact, total actions are unchanged, and
only the predicted `ls20` level is added. This is strong evidence that the
new authority gate is structurally narrow rather than a broad exploration
perturbation.

The complete 25-game run confirms the same isolation: 49/183 levels and
20.65827051873133/100, with all 24 non-target vectors exact and no action-cost
increase. The temporal CSP therefore adds one level without disturbing any
previously measured behavior.
