# Reflector-II minimal language

Status: Phase-1 source/serialization language. The runtime never interprets
text in its hot loop.

## 1. Design decision

The core language has three term constructors and three submission forms. It
does not have distinct syntax or runtime classes for concepts, relations,
actions, transformations, analogies, goals, or teacher hypotheses.

### Core terms

```ebnf
symbol      = identifier | quoted-string | integer | decimal ;
variable    = "?" identifier ;
atom        = symbol | variable ;
application = "(" symbol atom* ")" ;
term        = atom | application ;
```

Symbols are interned atoms. Variables exist only inside schema submissions.
An application is an ordered relational term. A schema body is an unordered,
duplicate-free finite conjunction of applications.

Phase 1 deliberately accepts flat applications only. Composition is expressed
by conjunction and shared variables rather than nested syntax; adding nested
terms later would require an explicit matcher/indexing decision. There are no
implicit side effects, negation-as-failure, loops, arbitrary code, or unbounded
quantification.

### Submission forms

```ebnf
fact-form     = "(" "fact" application metadata* ")" ;
schema-form   = "(" "schema" symbol "(" variable* ")"
                    application+ metadata* ")" ;
schema-dag-form = "(" "schema" symbol "(" variable* ")"
                    dag-entry+ metadata* ")" ;
dag-entry     = child-entry | relation-entry ;
child-entry   = "(" "child" symbol variable* ")" ;
relation-entry = "(" "relation" application ")" ;
evidence-form = "(" "evidence" symbol evidence-kind number metadata* ")" ;
metadata      = keyword term ;
keyword       = ":" identifier ;
evidence-kind = "support" | "contradiction" |
                "prediction-success" | "prediction-failure" ;
```

`fact`, `schema`, and `evidence` are compiler envelope operations, not nodes in
the epistemic ontology. A serialized store emits these same forms. Metadata is
cold-path annotation; Phase 1 recognizes `:source` and `:context` and rejects
unknown keys rather than ignoring them.

`schema-form` is retained for atomic/kernel patterns and compatibility.
`schema-dag-form` is the constructed-schema form: each `child` names one
existing reusable schema and supplies its interface-variable mapping in the
referenced schema's canonical variable order; each `relation` is a typed
parent-level constraint. Mixing the two body styles is rejected.

## 2. Formal semantics and compilation

| Construct | Denotation | Compiled representation | Status |
|---|---|---|---|
| symbol `s` | one interned identity | `kind=SYMBOL, symbol_id=k` | fundamental |
| variable `?x` | one substitution slot scoped to a schema | `kind=VARIABLE, ordinal=k` | fundamental |
| `(p a...)` | ordered application of head `p` | `kind=APPLICATION, head=symbol_id(p), child_offset, arity`; children in flat `int32` pool | fundamental |
| schema body | conjunction; true when every member unifies under one substitution | sorted tuple of application IDs, alpha-normalized and hash-consed | fundamental |
| `(fact t ...)` | add ground `t` to a named observation/evidence scope | transient fact ID plus provenance event; persistence is explicit | compiler envelope |
| `(schema n (...) t...)` | propose/retrieve the canonical conjunctive pattern | persistent schema row referencing canonical body roots | compiler envelope |
| `(evidence h k n ...)` | add signed local sufficient statistics to target hash/name | append-only evidence event and counter delta | compiler envelope |

Alpha-normalization repeatedly partitions variables by their relational
occurrences, argument positions, constants, and neighboring variable classes.
Only variables left in the same structurally symmetric class are permuted; the
lexicographically least encoding under those residual permutations is retained.
Canonical identity excludes display name, provenance, activation, and evidence
counters or candidate/promotion state. Thus an endogenous and teacher proposal
with the same body resolve to the same schema node while retaining both
provenance events.

Matching is positive conjunctive query evaluation. Each body application is
indexed by `(head, arity)` and may additionally use its ground argument
fingerprint. Variables unify by equality of canonical term IDs. Phase 1 limits
arity, body size, candidate facts per atom, and returned bindings; constructs
outside those limits fail closed with a resource event.

## 3. Everything richer is data

### Simultaneous descriptions

```lisp
(fact (Color region-7 Blue) :source sensor)
(fact (Connected region-7) :source sensor)
(fact (Form region-7 form-91ac) :source sensor)

(schema Colored (?x ?c) (Color ?x ?c) :source kernel)
(schema HasForm (?x ?f) (Form ?x ?f) :source endogenous)
```

Both schemas can bind and remain active. Neither is a parse root.

### Reusable composite

```lisp
(schema FormWithEnclosure (?x ?f ?h)
  (Form ?x ?f)
  (Enclosed ?h)
  (Inside ?h ?x)
  :source endogenous)
```

The readable name has no authority. The compiler stores one conjunction and
the endogenous composer stores one or more decomposition DAGs over child-schema
occurrences. Each occurrence records how its variables map to the canonical
variables above. `part` links are only a schema-level projection used for
activation; the occurrence DAG is the lossless construction record. A
shorthand such as `LWithHole(x) := ...` may be added to a UI, but it is not core
syntax. Teacher DSL can propose the same canonical body; a claimed derivation
becomes ordinary provenance and must be validated against existing child
schemas before it is installed.

The DAG is not an execution pipeline. It is a finite proof/decomposition of a
schema body. All child and parent schemas may be active simultaneously, and
the relational fact graph denoted by the body is allowed to contain cycles.

### Transformation / morphism

```lisp
(schema IntroduceEnclosure (?before ?after ?form ?n0 ?n1 ?action)
  (Domain ?before)
  (Codomain ?after)
  (Intervention ?action)
  (Before ?before Form ?form)
  (After ?after Form ?form)
  (Before ?before EnclosureCount ?n0)
  (After ?after EnclosureCount ?n1)
  (Less ?n0 ?n1)
  :source endogenous)
```

`Domain`, `Before`, `Less`, and `Intervention` are ordinary relation symbols.
The runtime recognizes no `PERFORATE` opcode. Preservation is shared-variable
structure (`?form` on both sides); increase is an explicit relation that can be
verified by the integer comparison kernel.

### Opaque action and learned effect

```lisp
(fact (Action ACTION_3) :source environment)
(schema ActionEffect (?s0 ?s1 ?x ?p0 ?p1)
  (Domain ?s0)
  (Codomain ?s1)
  (Intervention ACTION_3)
  (Before ?s0 Position ?x ?p0)
  (After ?s1 Position ?x ?p1)
  (Offset ?p0 ?p1 1 0)
  :source endogenous)
```

The token is not called `RIGHT` internally. A human-readable alias can be a
separate ordinary fact.

### Teacher proposal

```lisp
(schema PerforatedCandidate (?x ?h)
  (Shape ?x)
  (Enclosed ?h)
  (Inside ?h ?x)
  :source teacher:qwen)
```

This compiles identically to an endogenous schema. `:source` is retained and
the schema begins in the same weak-candidate state as an endogenous proposal.
The teacher cannot submit counters, activation, canonical IDs, executable code,
privileged flags, or prior weights.

### Prediction and falsification

Predictions use linked flat ground facts in a pending context:

```lisp
(fact (Predict prediction-12 schema-hash context-8) :source endogenous)
(fact (Expected prediction-12 After state-9 EnclosureCount 1)
      :source endogenous)
(evidence schema-hash prediction-failure 1
          :context context-8 :source environment)
```

These forms serialize runtime records; normal code creates them without
round-tripping through text.

### Explanations, goals, and experiments as data

The current parser deliberately has no privileged `explanation`, `goal`, or
`solution` form. A next-phase explanation is a conventional schema whose
ordinary applications identify its bound scope, preconditions, intervention,
preserved/changed relations, and projected successor. For example:

```lisp
(schema ContactDamages (?state ?next ?x ?y ?action)
  (Domain ?state)
  (Codomain ?next)
  (Intervention ?action)
  (Controlled ?x)
  (Orange ?y)
  (Contact ?state ?x ?y)
  (Before ?state Health ?x Healthy)
  (After ?next Health ?x Damaged)
  :source endogenous)

(schema AvoidDamageGoal (?state ?x)
  (GoalState ?state)
  (Controlled ?x)
  (Safe ?state ?x)
  :source endogenous)
```

`Domain`, `Codomain`, `GoalState`, `Controlled`, `Safe`, and `Contact` have no
reserved semantics: they are normal symbols whose use is grounded by evidence.
An explanation's currently selected bindings, pending shadows, and evaluation
state remain runtime records, just as a morphism's pending prediction does.
A candidate experiment is likewise a schema/morphism proposal plus ordinary
prospective predictions; it cannot directly install a policy or evidence.

This convention gives endogenous construction and a teacher/LLM one epistemic
currency. The compiler must continue to reject unknown metadata and must not
infer truth, priority, or executable code from a display name or teacher
provenance.

## 4. Fundamental versus sugar

Only symbol, variable, application, conjunction, and the submission envelopes
are fundamental. The following are explicitly syntactic sugar or conventions:

- `X : Region` -> `(Kind X Region)`
- `X -color-> Blue` -> `(Color X Blue)`
- named concept `Blue(X)` -> `(Color X Blue)` or a schema over it
- `preserve Form` -> a variable occupying the same `Before` and `After` slot
- `increase Count` -> `Before`, `After`, and `Less` applications
- `AND` -> membership in the same canonical schema body
- `MAP`, `REWRITE`, `ACTION`, and `PREDICT` -> ordinary schema/fact patterns
  plus runtime scheduling state

There is deliberately no general `OR` or negation in Phase 1. Alternatives are
separate schemas active in parallel. Explicit inequality/difference is a
positive relation verified by a kernel. This keeps matching monotone and
tractable.

## 5. Static and resource rules

- Applications have arity `0..8`; schema bodies contain `1..16` applications.
- Every declared variable must occur in the body. Variables are universal for
  matching and existential in the returned binding.
- Facts must be ground; all Phase-1 applications are flat.
- Source and context strings are length-bounded; numbers must be finite.
- Compilation is deterministic. Invalid or over-budget input produces no graph
  mutation.
- Text is parsed only at ingestion, debugging, and serialization boundaries.

## 6. Versioning

Serialized streams begin with a language version outside the term stream.
Phase 1 is `r2/0.2`. A new primitive term constructor or change in canonical
hash semantics requires a major version. New conventional predicate symbols do
not: they are data. Compiler-envelope metadata additions require a minor
version and must specify whether they affect evidence, never identity.

## 7. Schema DAG and projection example

```lisp
(schema LShape (?a ?b ?c)
  (child Segment ?a)
  (child Segment ?b)
  (child Corner ?c)
  (relation (EndpointOf ?c ?a))
  (relation (EndpointOf ?c ?b))
  (relation (Orthogonal ?a ?b))
  :source endogenous)

(schema PerforatedL (?a ?b ?c ?h)
  (child LShape ?a ?b ?c)
  (child Hole ?h)
  (relation (Inside ?h ?c))
  :source endogenous)
```

The compiler stores child schema IDs and interface maps once, then compiles the
child expansions plus relations into a bounded matcher slice. A partial runtime
binding is not serialized as a schema or a fact: it is a `SHADOW` record over
one schema ID with assignments, child-role states, parent-constraint states,
carrier, activation, provenance, and later `REIFIED` or `REFUTED` status.
Child-role state is `REIFIED` only by a child binding and otherwise `SHADOW`;
constraint state is `REIFIED` only by verification and otherwise `PROJECTED`.
The compiled atom expansion may complete a DAG check but does not define this
partial-binding ontology.
