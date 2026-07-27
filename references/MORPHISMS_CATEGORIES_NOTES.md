# Morphisms and categories implementation notes

These notes derive from the locally consulted 25-page excerpt of Jean Piaget,
Gil Henriques, and Edgar Ascher, *Morphisms and Categories: Comparing and
Transforming*, translated and edited by Terrance Brown, with a preface by
Seymour Papert (Lawrence Erlbaum Associates, 1992). The file contains front
matter, Papert's preface, Piaget's introduction, and the opening of Chapter 1;
it is not the complete 229-page book. The repository does not redistribute it.

## The decisive distinction

Piaget separates two constructive functions:

- **operatory transformations** modify or generate objects or contents;
- **morphisms** compare objects, states, transformations, or their results
  without thereby modifying the compared contents.

Morphisms are not inert. A higher-order morphismic transformation can modify,
compose, or create the instruments of comparison themselves. In a form/content
hierarchy, a form at one level can become content for a higher form.

For Reflector, this means:

- an environment action and its learned effect approximate an operatory
  transformation;
- a procedure composes transformations in time toward a goal;
- a schema family currently groups similar transformations, but does not yet
  represent a mapping between them;
- a genuine higher-order comparison must have typed source and target
  structures and be composable with compatible comparisons.

Grouping, similarity, or macro execution alone is not a morphism.

## Three proposed construction levels

Piaget's introduction describes three broad forms:

1. **intramorphic** — isolated correspondences over observables; they need not
   be complete or univocal, do not compose systematically, and may tolerate
   unnoticed contradiction;
2. **intermorphic** — correspondences among correspondences begin to compose,
   producing local necessity, but without general closure or freely chosen
   source and endpoint;
3. **transmorphic** — the subject operates on morphisms using generalized
   transformations; morphisms themselves become content for higher-order
   construction.

These names should not enter Reflector merely as labels. They suggest observable
capabilities:

- isolated source/target mappings;
- typed composition when endpoints match;
- identity mappings;
- closure and associativity over a bounded learned structure;
- transfer of a comparison independently of the original concrete contents;
- construction of an operator whose inputs are prior mappings.

## Piaget/Papert caution

Papert explicitly raises the danger that category-theoretic language could be
used as a superficial metaphor. Reflector should therefore adopt only
mathematical structure it can execute and test. A proposed category-like
abstraction must expose objects, arrows, domains, codomains, identities, and
composition, and its composition must satisfy identity and associativity tests
on the represented cases.

Passing those algebraic tests would establish a small formal structure, not
psychological fidelity and not the explanatory adequacy of category theory for
cognitive development.

## Architectural consequence

The next higher-order representation should be a bounded **transformation
system** and **comparison graph**:

```text
observed transition
  -> transformation(source predicates, action, target predicates)
  -> comparison(source transformation, target transformation, preserved map)
  -> composed comparison, when codomain/domain types agree
```

The structure should keep two operations separate:

- temporal composition of transformations for achieving goals;
- structural composition of comparisons for relating transformations.

They may exchange information, but neither should silently stand in for the
other.

## Falsification requirements

A morphism mechanism is useful only if:

1. learned comparisons predict preserved relationships in held-out contents;
2. composed comparisons outperform isolated similarity matching;
3. invalid endpoint compositions are rejected;
4. identity and associativity hold for every accepted finite case;
5. disabling access to comparison objects removes the effect while preserving
   all lower-level procedures and schemas;
6. the additional representation pays its complexity and runtime costs;
7. official offline Kaggle compatibility remains intact.
