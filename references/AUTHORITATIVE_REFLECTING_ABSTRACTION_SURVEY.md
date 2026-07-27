# Authoritative online survey: reflecting abstraction

Survey date: 2026-07-27.

This survey deliberately prefers primary texts, institutional archives,
scholarly books, and peer-reviewed research. It excludes Wikipedia, blogs,
commercial summaries, anonymous uploads, and papers that merely use
“reflection” in an unrelated metacognitive or software-reflection sense.

## Primary record

### Piaget's definitions and general conclusions

The Fondation Archives Jean Piaget gives the central two-part definition:
reflecting abstraction projects a coordination from a lower plane and
reconstructs or reorganizes it on a higher plane.

- [Fondation Archives Jean Piaget: abstraction
  réfléchissante](https://www.fondationjeanpiaget.ch/fjp/site/oeuvre/index_notions_nuage.php?NOTIONID=11)
- [Piaget, *Recherches sur l'abstraction réfléchissante*, general
  conclusions](https://www.unige.ch/piaget/piaget1977RARB_16)

The full conclusions distinguish:

- empirical abstraction from object properties or material aspects of action;
- pseudo-empirical abstraction from properties that the subject's actions
  introduced into the observed arrangement;
- reflecting abstraction from coordinations of actions;
- reflected abstraction when the result itself becomes an object of conscious
  comparison or formulation.

They also emphasize that construction proceeds through alternating
differentiation and integration, increasing composition and reversibility, and
operations on prior operations.

### Equilibration and contradiction

Piaget's 1975 account makes empirical observables and inferred coordinations
interact at every level. When an observation resists the current system, the
strong response is not to ignore it but to reorganize the system so the former
perturbation becomes an integrated variation. Positive assertions must be
balanced by their corresponding negations.

- [Piaget, *L'équilibration des structures cognitives*, chapter
  II](https://www.unige.ch/piaget/piaget1975ESC_03)
- [Piaget, *L'équilibration des structures cognitives*, chapter
  V](https://www.unige.ch/piaget/piaget1975ESC_06)

### Success, understanding, procedures, and structures

Practical success can precede conceptual understanding. Understanding becomes
stronger when it can explain why and how, anticipate beyond the observed
trajectory, and program the action as a whole in a changed situation.

- [Piaget, *Réussir et comprendre*, general
  conclusions](https://www.unige.ch/piaget/piaget1974RCO_14)

Inhelder and Piaget distinguish temporal, goal-directed procedures from
atemporal structures connecting transformations. They remain interdependent:
procedures use structures, while procedures can discover structures. Modal
judgments—possible, impossible, necessary, and pseudo-necessary—provide
behavioral evidence for structure that is not reducible to a memorized
procedure.

- [Inhelder & Piaget, “Procédures et
  structures”](https://www.unige.ch/piaget/piaget1979a05)

## Authoritative elaborations and criticisms

### Campbell and Bickhard: knowing levels

Campbell and Bickhard argue that a control hierarchy is not a hierarchy of
knowing. Their process criterion is that organization implicit at one level
becomes explicitly represented and available as an object of knowing at the
next. They also criticize Piaget for leaving the reflective process partly
metaphorical and distinguish within-level learning from ascent between knowing
levels.

- [Campbell & Bickhard, *Knowing Levels and Developmental
  Stages*](https://www.ecointeractivism.com/_files/ugd/46def2_257f342e66a74490988abba2e6c10c49.pdf)
- [Publisher record and DOI](https://doi.org/10.1159/000412689)

For Reflector this is a decisive anti-inflation rule: a planner that invokes a
longer macro is still a controller. A higher knowing level requires the agent
to represent, compare, transform, or reason about its own operative
organization.

### von Glasersfeld: re-presentation and awareness

Von Glasersfeld carefully separates recognizing an experiential pattern,
spontaneously re-presenting it without the object present, and consciously
making properties of that representation an object of thought. His
interpretation reinforces that abstraction type cannot be inferred from
surface symbolic form alone.

- [von Glasersfeld, “Abstraction, Re-Presentation, and
  Reflection”](https://files.eric.ed.gov/fulltext/ED306120.pdf)

### Dubinsky and APOS: constructive operations

Dubinsky's research program makes a useful, empirically motivated decomposition
of mathematical construction: interiorization, coordination, encapsulation,
generalization, and reversal. Actions become processes; processes may be
coordinated or reversed; a process treated as a whole becomes an object; and
schemas remain dynamic, reconstructible systems rather than static lists.

- [Dubinsky, “Reflective Abstraction in Advanced Mathematical
  Thinking”](https://people.math.wisc.edu/~rwilson/Courses/Math903/ReflectiveAbstraction.pdf)

This taxonomy is an engineering hypothesis for Reflector, not a claim that
Piaget himself supplied a complete computational algorithm.

### Simon, Tzur, Heinz, and Kinzel: activity-effect reflection

This peer-reviewed elaboration treats reflection on activity-effect
relationships as a concrete mechanism for conceptual learning. Later
task-sequence work stresses starting from activities already available to the
learner, rather than teaching the target abstraction directly.

- [Journal record: “Explicating a Mechanism for Conceptual
  Learning”](https://doi.org/10.2307/30034818)
- [Simon, “An approach to the design of mathematical task
  sequences”](https://doaj.org/article/2e884c4d0bfc4e31a78a1ab4b20c3166)

Reflector's action/effect schemas are a plausible substrate for this mechanism,
but the reflection pass must operate on relations among those records and be
tested on tasks that require the new relation.

### Computational-thinking literature

The peer-reviewed computational-thinking treatment rejects abstraction as mere
feature extraction and uses reflective abstraction/APOS to emphasize the
construction of executable processes and objects.

- [Çetin & Dubinsky, “Reflective abstraction in computational
  thinking”](https://doi.org/10.1016/j.jmathb.2017.06.004)

## Synthesis for Reflector

The literature supports six distinct data roles:

1. **observable** — an empirical property of scene or material action;
2. **activity** — a temporally situated action or procedure;
3. **effect** — an observed change attributable to activity;
4. **coordination** — a relation among activities/effects, including order,
   composition, compensation, or invariance;
5. **operative structure** — a reusable system of coordinated transformations;
6. **knowing-level object** — an operative structure made explicit so the
   agent can compare, transform, compose, reverse, or criticize it.

Reflector currently represents the first five unevenly. It does not yet provide
strong evidence for the sixth.

## Ranked implementation consequences

1. Add an **equilibration ledger** recording prediction failures,
   contradictions, contextual negations, and whether they were ignored,
   locally accommodated, or integrated by structural reorganization.
2. Keep **procedures and structures distinct**. Procedures optimize a temporal
   goal; structures encode relations among transformations and modal reachability.
3. Give accepted abstractions explicit **construction operators**:
   interiorize, coordinate, encapsulate, generalize, and reverse.
4. Require **modal and counterfactual tests**: what is reachable, impossible
   under current operators, invariant under repetition, or necessary across
   alternative procedures?
5. Create a genuine **knowing-level object** whose inputs are learned schemas,
   families, or procedures—not pixels—and whose output changes how those
   structures are compared or transformed.
6. Validate with **activity-effect task sequences**, complete-programming
   transfer, reversal, composition, and perturbation/accommodation tests.

All mechanisms must remain deterministic, bounded, serializable, and inside
the same offline `SymbolicPolicy` exported to Kaggle.
