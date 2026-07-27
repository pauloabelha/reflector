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
schemas yield cross-context schema families; concepts yield typed parents; and
repeated concrete rotation predicates can yield a compositional orientation
operator. Each structure records its members, evidence, raw and compiled
description length, complexity, and utility. This is reflecting abstraction in
the repository's explicit engineering sense, not a claim that Piaget's full
developmental account has been reproduced.

## Operational reflecting abstraction

Reflector separates five serializable levels:

1. observations become objects, attributes, and bounded relations such as
   `left_of`, `above`, `aligned_x`, `aligned_y`, and `touching`;
2. action/effect evidence becomes empirical schemas;
3. recurrent concepts with the same evidence-backed kind can acquire a typed
   parent;
4. schemas with the same action and result predicates across distinct contexts
   can compile into a schema family;
5. repeated `rotated_90`, `rotated_180`, and `rotated_270` predicates can
   compile into `orientation_delta(object,k)` with composition in ℤ₄.

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

The compositional operator currently reduces representation length and exposes
an algebra to later planners; it does not yet transform raw frames or prove
transfer to a held-out game. Schema families similarly compile repeated
structure but are not yet macro-actions. Those are measured future steps, not
implied capabilities.

## Current operational approximations

Reflector treats a causal hypothesis as a difference between an event's
empirical rate following one action and its rate following observed alternative
actions. Confidence is evidence-discounted; this is causal attribution under
active observational controls, not proof of interventionally complete
causation.

Temporal hypotheses currently represent one-transition precedence. Planning is
bounded search over learned action→event operators plus sufficiently reliable
temporal implications. Goals are presently limited to level advancement.

Recoverable epistemic redundancy currently counts repeated action-effect
rediscovery, equivalent schemas across contexts, repeated plan computation, and
concept evidence that existed before compilation. Counterfactual replay injects
a final concept at its first supporting transition and measures description
length and repeated-work savings. It reports zero action savings because a
recorded trace cannot establish outcomes of actions that were never taken.
These constraints are intentional safeguards against inflated abstraction
claims.

## Primary grounding

Drescher's primary AAAI account distinguishes a predictive schema from a rule
that commands an action: a schema estimates what would follow if an action were
taken in a satisfied context. Reflector preserves that separation, empirical
reliability, curiosity pressure, and the ability to build later structures from
earlier ones, while replacing exhaustive item statistics with bounded typed
stores suitable for ARC grids.

Piaget's *Studies in Reflecting Abstraction* motivates construction from
coordinated relationships among prior structures. Reflector translates that
direction into evidence-bearing compilation passes; it does not infer that an
MDL-positive schema family is psychologically equivalent to human reflective
abstraction.

See [references/README.md](references/README.md) for primary links and the
limits on their use.
