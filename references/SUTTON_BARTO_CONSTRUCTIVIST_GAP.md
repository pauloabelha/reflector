# Sutton–Barto and the constructivist gap

Source read in full: Richard S. Sutton and Andrew G. Barto,
*Reinforcement Learning: An Introduction*, attached 352-page “Second edition,
in progress” PDF dated 2014–2015. This is an earlier draft, not the final 2018
second edition. Chapters 12 and 13 are placeholders in this file, so no claims
are attributed to absent text.

## What the book establishes

The book gives a coherent computational account of learning from interaction:
an agent acts in a closed loop, consequences unfold over time, exploration must
be balanced with exploitation, learned models can support planning, and
learning and planning can share incremental backup machinery. Its unified view
organizes the covered methods around value functions, backups along real or
possible trajectories, and generalized policy iteration.

This is stronger than a simple stimulus–response behaviorism. State can include
memory, models can predict consequences, planning can operate on simulated
experience, and temporally extended behavior is explicitly recognized.

## The gap the book states itself

The decisive limitation is representational. Chapter 3 says that the choice of
state and action representations strongly affects performance, but the book
focuses on learning behavior after those representations have been selected.
Its Markov discussion explicitly leaves construction, change, and learning of
the state signal outside scope. Chapter 15 returns to this as an open frontier:
making do with an existing representation is comparatively understood; the
constructive part remains unclear.

The reward hypothesis also makes cumulative scalar reward the formal account
of purpose. That is useful for control, but it does not explain how an agent
constructs a new object, relation, invariant, negation, schema, operation, or
level of description, nor why such a construction becomes necessary.

## What Piaget, Papert, and Drescher add

The shared missing idea is not “symbols plus reward.” It is that learning can
change the system of meanings in which states, actions, and goals are
expressed.

- Piagetian equilibration treats contradiction as pressure to reorganize a
  structure, differentiating and reintegrating it, rather than merely lowering
  the value of a response.
- Reflecting abstraction projects coordinations of action to a new level where
  they can become objects of further comparison, composition, and
  transformation.
- Papert's constructionism emphasizes executable, inspectable objects-to-think-
  with and the recursive construction of powerful representations.
- Drescher operationalizes part of this direction through predictive schemas,
  explicit context/action/result structure, synthetic items, marginal
  attribution, and machinery that can build later structures from earlier
  ones.

On this view, reinforcement has at least two non-interchangeable roles:

1. **pragmatic selection**: did interaction advance an externally grounded
   task?
2. **structural equilibration**: which explicit prediction was confirmed or
   contradicted, what condition explains the contradiction, and does a proposed
   reorganization improve prediction, intervention, reuse, or compression?

Collapsing these into one return recreates the problem. A concept is not good
because it carries reward. It earns retention because it explains evidence and
supports new competence, while task success remains an independent check.

## Contract for Reflector

Reflector should borrow temporal credit, active experimentation, model-based
planning, replay, and incremental computation from reinforcement learning
without turning symbolic cognition into a Q-table.

Structural commitments must therefore remain typed and falsifiable:

- positive and negative propositions are frozen before the outcome;
- confirmation, contradiction, novelty, pragmatic progress, and epistemic
  discovery are recorded in separate channels;
- contradictions can construct conditional differentiations;
- accepted structures pay a complexity cost and must demonstrate prediction,
  intervention, composition, reuse, or compression;
- no sensory change is silently treated as reward;
- no single scalar “concept value” decides truth, meaning, and task utility.

The first code consequence is explicit negation. When accommodation learns
“under condition C, effect P does not occur,” absence of P is now a recorded
confirmation and occurrence of P is a recorded contradiction. The suppression
is no longer an invisible policy tweak and can itself undergo later
equilibration.
