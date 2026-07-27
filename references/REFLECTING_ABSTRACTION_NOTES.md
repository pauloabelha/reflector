# Reflecting-abstraction implementation notes

These notes derive from the locally consulted 35-page excerpt of Jean Piaget's
*Studies in Reflecting Abstraction*, edited and translated by Robert L.
Campbell (Psychology Press, English translation 2001). The file contains the
front matter and Campbell's introductory chapter, not the complete 327-page
volume. The repository does not redistribute it.

## Stronger operational definition

Piaget's distinction is not simply between concrete and abstract
representations. Empirical abstraction selects properties of objects.
Reflecting abstraction operates on actions or coordinations among actions and
has two coupled phases:

1. **projection** carries a lower-level coordination into a higher-order
   representational level;
2. **reflection** reorganizes it there rather than merely copying or naming it.

The resulting construction should enable a novel composition, differentiation,
integration, generalization, mobility, or reversibility. Positive compression
is useful evidence that a representation is economical, but is insufficient by
itself.

Reflecting abstraction can itself become the object of another construction.
Campbell distinguishes:

- reflecting abstraction: construction from coordinated action;
- reflected abstraction: higher-order comparison or reconstruction of products
  of prior reflecting abstraction;
- metareflection: reflection on reflected abstractions.

These are not labels to infer from nesting depth. A claimed developmental level
needs independent behavioral evidence.

## Mapping to Reflector

- Scene objects, colors, and shapes are primarily empirical abstractions.
- Action/result schemas describe operative interaction, but an individual
  schema is not yet reflecting abstraction.
- A schema family is a reflecting-abstraction candidate when it projects
  coordination across concrete action/result episodes and reorganizes them into
  a context-bearing operator that improves transfer.
- A procedure is a candidate when it reorganizes the order of successful
  actions into a reusable controller; mere sequence memorization is not enough.
- An orientation algebra is a stronger candidate because it is constructed from
  transformations and supports composition and inversion.
- A language revision would approach reflected abstraction only if it compares
  and reorganizes already accepted abstractions and produces an independently
  measured behavioral or representational effect.

The six serializable levels in `THEORY.md` are therefore engineering strata,
not Piagetian stages.

## Acceptance and falsification gates

An accepted Reflector abstraction should eventually expose:

1. the lower-level action coordinations serving as evidence;
2. an explicit projection into a higher-order representation;
3. the reorganization or new operation supplied at that level;
4. a measurable gain in transfer, composition, reversibility, prediction,
   control, or description length;
5. positive and negative applicability evidence;
6. a way to revise or retire an over-broad, over-narrow, or otherwise erroneous
   construction.

The v2 procedure and novel-context ablations test part of item 4. Dependency
edges and evidence IDs cover part of item 1. Projection/reorganization records,
inversion tests, and abstraction-specific error correction remain open work.

## Research consequences

- Track differentiations and integrations together: specialization without
  reintegration is not equilibration.
- Treat contradictions and failed applicability as first-class evidence, not
  merely low confidence.
- Test higher-order abstraction with paired tasks that require explicit reuse
  or comparison among previously learned operations.
- Do not equate a more advanced representation with a correct one. Reflecting
  abstractions must remain falsifiable and degradable.
- Keep procedures and atemporal structures distinct in the data model until
  their relationship is empirically justified; Campbell identifies this as an
  unresolved problem in Piaget's late system.
