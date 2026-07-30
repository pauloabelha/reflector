# Research references

Reflector translates these sources into testable software contracts; it does
not treat them as authority for claims the implementation has not measured.

- Gary L. Drescher, [A Mechanism for Early Piagetian
  Learning](https://cdn.aaai.org/AAAI/1987/AAAI87-052.pdf), AAAI 1987. This is
  the primary concise account used for the distinctions among schemas,
  empirical reliability, extended contexts/results, plans, and synthetic
  items.
- Gary L. Drescher, [Made-Up Minds: A Constructivist Approach to Artificial
  Intelligence](https://mitpress.mit.edu/9780262041201/made-up-minds/), MIT
  Press, 1991. The publisher description and book motivate empirical concept
  extension, marginal attribution, synthetic items, and composite actions.
- Robert Matthew Ramstad, *A Constructivist Approach to Artificial Intelligence
  Reexamined*, MIT/LCS/TR-563, 1993. The implementation report is used
  especially for its distinction between reproduced internal structures and
  demonstrated goal-directed behavior.
- Jean Piaget, Gil Henriques, and Edgar Ascher, *Morphisms and Categories:
  Comparing and Transforming*, translated and edited by Terrance Brown, 1992.
  The locally consulted file is a 25-page excerpt containing Papert's preface,
  Piaget's introduction, and the opening of Chapter 1, not the complete book.
- Jean Piaget et al., [Studies in Reflecting
  Abstraction](https://www.routledge.com/Studies-in-Reflecting-Abstraction/Campell/p/book/9781138877375),
  English translation of *Recherches sur l'abstraction réfléchissante* (1977).
  Reflector borrows the direction of constructing knowledge from coordinated
  relationships among prior structures, not a claim of psychological fidelity.
  The locally consulted file contains only the front matter and Campbell's
  26-page theoretical introduction, not the complete book.
- Richard S. Sutton and Andrew G. Barto, *Reinforcement Learning: An
  Introduction*, locally consulted 352-page “Second edition, in progress”
  draft dated 2014–2015. It is used to distinguish value/policy improvement
  from constructive change to the agent's representational language.

The repository does not redistribute copyrighted book or thesis files. Add
locally obtained research material under `references/local/`, which is ignored,
and record only derived implementation decisions that can be tested.

The current derived decisions and explicit non-equivalences are in
[`SCHEMA_MECHANISM_NOTES.md`](SCHEMA_MECHANISM_NOTES.md) and
[`REFLECTING_ABSTRACTION_NOTES.md`](REFLECTING_ABSTRACTION_NOTES.md).
The broader primary/peer-reviewed online sweep and its ranked implementation
consequences are in
[`AUTHORITATIVE_REFLECTING_ABSTRACTION_SURVEY.md`](AUTHORITATIVE_REFLECTING_ABSTRACTION_SURVEY.md).
The transformation/morphism distinction and its executable category-law gate
are in [`MORPHISMS_CATEGORIES_NOTES.md`](MORPHISMS_CATEGORIES_NOTES.md).
The reinforcement-learning comparison and non-scalar structural-credit
contract are in
[`SUTTON_BARTO_CONSTRUCTIVIST_GAP.md`](SUTTON_BARTO_CONSTRUCTIVIST_GAP.md).
The apples-to-apples ARC-AGI-3 baseline protocol is in
[`SYMBOLIC_ARC3_COMPARISON.md`](SYMBOLIC_ARC3_COMPARISON.md). The proposed
hierarchical algorithm derived from the local paper corpus is in
[`REFLECTIVE_CAUSAL_HRL.md`](REFLECTIVE_CAUSAL_HRL.md).
