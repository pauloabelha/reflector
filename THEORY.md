# Theory

Reflector separates two learning timescales.

**Ontogeny** is learning within an unfamiliar game. The deployed symbolic agent
observes consequences of actions, builds explicit items and schemas, proposes
experiments, and reuses discovered structure while the episode is running.

**Phylogeny** is development across evaluated descendants. An optional external
LLM may analyze traces and propose structured mutations, but it is evolutionary
pressure rather than the deployed reasoner. Only validated symbolic mechanisms
enter descendants.

**Reflecting abstraction** is the construction of reusable structure from
relationships among existing structures: observations, concepts, schemas,
families of schemas, and eventually the language that expresses them. A label
alone is not an abstraction. Reflector will require explicit evidence,
dependencies, measurable compression, predictive, or planning effects, and a
complexity charge.

The practical target is recoverable epistemic redundancy: information that an
agent's history established but its current representation failed to retain or
reuse. Counterfactual replay asks whether a proposed concept, schema family, or
language operator would have reduced actions, search, runtime, error, or
description length had it existed earlier.

The current agent implements a bounded first operational step across those
levels. Observations yield persistent objects and typed spatial relations;
schemas yield cross-context schema families; concepts yield typed parents;
repeated concrete rotation predicates can yield a compositional orientation
operator; and repeated successful trajectories can compile into evidence-gated
procedures. Each structure records its members, evidence, raw and compiled
description length, complexity, and utility. These are operational candidates
for reflecting abstraction, not a claim that Piaget's developmental account
has been reproduced.

## Operational reflecting abstraction

Reflector separates six serializable engineering strata:

1. observations become objects, attributes, and bounded relations such as
   `left_of`, `above`, `aligned_x`, `aligned_y`, and `touching`;
2. action/effect evidence becomes empirical schemas;
3. recurrent concepts with the same evidence-backed kind can acquire a typed
   parent;
4. schemas with the same action and result predicates across distinct contexts
   can compile into a schema family;
5. repeated `rotated_90`, `rotated_180`, and `rotated_270` predicates can
   compile into `orientation_delta(object,k)` with composition in ℤ₄;
6. repeated multi-step trajectories ending in environment-grounded progress
   can compile into a procedure whose applicable suffix is available to the
   planner.

Acceptance is minimum-description-length-inspired rather than a full Bayesian
model:

```text
utility = raw description − compiled description
```

The compiled description includes the abstraction definition, residual
arguments or contexts, member references, and a configurable complexity
pressure. Schema-family savings are additionally weighted by empirical
reliability. Non-positive proposals are discarded. Dependency edges connect each
accepted abstraction to the schemas or concepts that paid for it. A language
version is appended only when the accepted operator set changes.

These strata are not Piagetian developmental stages. Under the stronger
source-derived criterion, compression is evidence of economy but is not
sufficient evidence of reflecting abstraction. A qualifying construction must
project a coordination of actions into a higher-order representation,
reorganize it there, and demonstrate a new behavioral or structural capacity
such as transfer, composition, differentiation with reintegration, or
reversibility. Reflector currently records evidence and dependencies but does
not yet serialize projection and reorganization as separate operations.

Accepted structures are compiled forward rather than merely displayed.
Functional concepts whose defining action applies become `synthetic_item`
terms in later schema contexts. Once the orientation operator is accepted,
later concrete rotation events are stored as
`orientation_delta(object,k)`. Reliable schema families contribute their
abstract result predicates and confidence to the same bounded planner used by
the Kaggle policy. MDL-positive procedures contribute evidence-gated plans to
that same policy.

This closes an internal reuse loop. The preregistered v2 synthetic confirmation
supports cross-layout family transfer and procedure efficiency under ablation,
but does not prove transfer to an ARC game. Schema families remain predictive
operators rather than macro-actions, and concept terms currently encode
availability for their defining action rather than a complete latent-state
semantics.

## Current operational approximations

Reflector treats a causal hypothesis as a difference between an event's
empirical rate following one action and its rate following observed alternative
actions. Confidence is evidence-discounted; this is causal attribution under
active observational controls, not proof of interventionally complete
causation.

Temporal hypotheses currently represent one-transition precedence. Planning is
bounded search over learned action→event operators, sufficiently reliable
temporal implications, and learned successful procedures. Goals are presently
limited to level advancement. A new-frame event can provide epistemic
exploration pressure, but sensory change has no external result value.

The procedure controller is deliberately smaller than Drescher's composite
action mechanism. It can choose a context-matching suffix among learned
procedures, but does not yet perform opportunistic proximity search with
separate estimates of time, reliability, cost, controller degradation, and
repair.

Recoverable epistemic redundancy currently counts repeated action-effect
rediscovery, equivalent schemas across contexts, repeated plan computation, and
concept evidence that existed before compilation. Counterfactual replay injects
a final concept at its first supporting transition and measures description
length and repeated-work savings. It reports zero action savings because a
recorded trace cannot establish outcomes of actions that were never taken.
These constraints are intentional safeguards against inflated abstraction
claims.

## Primary grounding

Drescher's primary AAAI account, *Made-Up Minds*, and Ramstad's reimplementation
distinguish a predictive schema from a rule that commands an action: a schema
estimates what would follow if an action were taken in a satisfied context.
Reflector preserves that separation, empirical reliability, curiosity pressure,
and the ability to build later structures from earlier ones, while replacing
exhaustive item statistics with bounded typed stores suitable for ARC grids.

The current `synthetic_item` term is not a Drescher-faithful synthetic item. It
does not yet reify a host schema's validity conditions with explicit
on/off/unknown state, implicit activation, and duration. The name is retained as
an implementation-level functional concept, and this non-equivalence is a
tracked research gap.

Likewise, the current language-history hierarchy is not by itself evidence of
Piaget's reflected abstraction or metareflection. Those claims require
independently tested comparisons and reorganizations among products of earlier
abstraction; representational nesting alone does not establish a developmental
level.

Piaget's *Studies in Reflecting Abstraction* motivates construction from
coordinated relationships among prior structures. Reflector translates that
direction into evidence-bearing compilation passes; it does not infer that an
MDL-positive schema family is psychologically equivalent to human reflective
abstraction.

See [references/README.md](references/README.md) for primary links and
[references/SCHEMA_MECHANISM_NOTES.md](references/SCHEMA_MECHANISM_NOTES.md)
and
[references/REFLECTING_ABSTRACTION_NOTES.md](references/REFLECTING_ABSTRACTION_NOTES.md)
for the source-to-contract maps and limits on their use.
