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
dependencies, measurable predictive/planning effects, and a complexity charge.

The practical target is recoverable epistemic redundancy: information that an
agent's history established but its current representation failed to retain or
reuse. Counterfactual replay asks whether a proposed concept, schema family, or
language operator would have reduced actions, search, runtime, error, or
description length had it existed earlier.

The current canonical-action baseline is not claimed to implement those deeper
ideas. It establishes the competition-valid organism into which they can be
introduced and measured.

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
