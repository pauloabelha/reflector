# Constructive symbolic reinforcement

## Source read

The supplied `SuttonBartoIPRLBook2ndEd.pdf` was inspected end to end.  It is
not the completed 2018 second edition: its title page says “Second edition, in
progress” and dates it 2014–2015.  Chapters 10, 12, and 13 are placeholders,
and sections 15.2–15.4 have headings but no bodies.  Conclusions below are
therefore claims about this supplied draft.  Missing draft material is not
evidence that the completed edition omits the same material.

The substantive chapters were read with particular attention to:

- the agent/environment interface, goals, rewards, returns, and Markov state;
- bandit, dynamic-programming, Monte-Carlo, temporal-difference, eligibility
  trace, planning, and function-approximation updates;
- afterstates, learned models, exploration, generalization, and hierarchy;
- the application case studies and the explicit open problems in Chapter 15.

## What reinforcement learning gets right

Reflector must not define itself through a caricature of reinforcement
learning.  The book begins with active sensorimotor interaction and causal
consequences, not passive stimulus classification.  Its agents can contain
memory, learned models, planning, predictions, internal state, abstract
actions, and temporally extended credit.  Temporal-difference errors are not
mere immediate pleasure/pain associations.  The framework also permits
symbolic states and mental actions.

Several mechanisms should be retained:

- online learning from the consequences of self-selected actions;
- explicit prediction before outcome;
- delayed credit through bounded eligibility traces;
- integration of acting, model learning, and planning;
- active experiments rather than reliance on a labelled teacher;
- transfer through afterstates and appropriately shared representations;
- continual interaction between what is predicted and what is done.

This is already substantially richer than methodological behaviorism.

## The exact limitation admitted by the draft

The central limitation is not the absence of symbols.  It is that the
representational ontology is normally selected before the learning rule is
applied.

Chapter 3 says that the state is supplied by a preprocessing system and that
the book does not address constructing, changing, or learning the state
signal.  It focuses on choosing an action after state, action, and reward
representations have been selected.  Chapter 9 likewise treats feature choice
as an important injection of prior domain knowledge.  Chapter 15 finally
divides the non-Markov problem into “making do” with the current
representation and constructing a better one; it calls the constructive part
unclear and wide open.

The reward hypothesis adds a second restriction: all goals and purposes are
treated as maximization of expected cumulative scalar reward.  This is a
powerful engineering reduction, but it deliberately collapses distinctions
among success, prediction, coherence, explanation, necessity, possibility,
and understanding.

Thus the book's dominant update has the form:

> improve a value, policy, or model inside a supplied state/action/goal
> language.

The missing update has the form:

> when the current language cannot assimilate the consequences of action,
> construct and test a better language of objects, predicates, actions, and
> relations among actions.

## What Piaget, Papert, and Drescher add

### Piaget

Learning is not only adjustment of behavior inside a fixed problem.  An
action is coordinated with other actions; that coordination can be projected
and reflected upon; the resulting operation can itself become an object of a
new operation.  Disequilibrium is therefore potentially a signal that the
scheme of interpretation must be reorganized, not merely weakened.

Assimilation without accommodation is the analogue of fitting every outcome
into the current state space.  Accommodation differentiates and reorganizes
schemes while preserving what remains valid.  Reflecting abstraction changes
the space of possibilities the subject can represent.

### Papert

Knowledge is constructed through making and debugging inspectable objects in
a microworld.  For Reflector, learned schemas, synthetic items, procedures,
transformations, and comparisons must be executable public objects—not
hidden labels whose only justification is improved return.  The system should
be able to operate on and revise these objects.

### Drescher

The schema mechanism makes the constructive step computational.  Marginal
attribution supports context/action/result schemas; synthetic items represent
otherwise unobserved validity conditions; synthetic actions package reliable
extended activity.  Credit belongs to a specific predicted result under a
specific context, not to a state/action pair through a single fungible value.

Together these views suggest **structural credit assignment**: reinforce the
representational construction that made a discriminating prediction or
enabled a new operation, and accommodate the construction whose applicability
conditions were contradicted.

## Reflector doctrine

Reflector may use external score to identify the competition goal and may use
numeric confidence for calibrated evidence.  It must not treat all learning
signals as one interchangeable reward.

Each transition is assessed on separate typed channels:

1. **Pragmatic:** did an externally specified goal advance or regress?
2. **Predictive:** which proposition-level predictions were confirmed or
   contradicted?
3. **Epistemic:** was a new state, effect, distinction, or controllable
   intervention discovered?
4. **Coherence:** can the result be assimilated by current schemas, or is
   accommodation required?
5. **Compression:** did a retained construction shorten an evidence-grounded
   account while preserving predictive and control utility?
6. **Modal:** did an operation change what the agent can establish as
   reachable, impossible, reversible, or necessary?

These records are not summed into a universal cognitive reward.  Action
selection may use a deterministic arbitration policy, but structural learning
uses the channel semantics directly.

## Constructive prediction-error protocol

For every selected action:

1. serialize the pre-action context and proposition-level prediction;
2. preserve the schemas and abstractions that licensed the prediction;
3. compare the later observation with that prediction;
4. record confirmations and contradictions before learning from the outcome;
5. route contradiction through a bounded response ladder:
   - `retain`: insufficient evidence to alter the structure;
   - `specialize`: narrow an overgeneral schema;
   - `differentiate`: introduce a tested context distinction;
   - `construct`: propose a synthetic validity item or action;
   - `integrate`: relate specialized cases under a conditional operator;
   - `retire`: remove an unsupported construction from the operative path;
6. assign structural credit only when a counterfactual ablation shows that the
   construction improved held-out prediction, control, or compression.

An eligibility trace may carry typed responsibility across time, but it must
name propositions and structures.  It must not be a decaying scalar trace
whose sole target is cumulative reward.

## Falsifiable distinction from scalar reinforcement

The decisive diagnostics keep reward histories equal while changing the
causal or representational structure.

- **Aliased context:** two hidden contexts produce the same observations and
  rewards until a diagnostic intervention.  Success requires constructing a
  validity distinction, not increasing a value estimate.
- **Same return, different reason:** two policies earn identical return but
  only one learned model predicts the intervention outcome.  Model selection
  is scored by held-out proposition accuracy.
- **Perturbation accommodation:** a learned regularity fails in one new
  context.  The agent must preserve the old valid domain, specialize the new
  one, and integrate both; global confidence decay fails.
- **Delayed structural credit:** an early experiment enables a later
  distinction without changing interim reward.  A typed evidence trace must
  credit the experiment and construction.
- **Knowing-level intervention:** controllers remain intact, but access to
  their serialized structure is ablated.  A task requiring composition or
  reversal of learned operators should then fail.

If Reflector cannot outperform fixed-ontology and scalar-credit ablations on
these tests, “constructive symbolic reinforcement” is only terminology and
must be rejected.

