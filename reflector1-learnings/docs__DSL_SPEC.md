# Schema Calculus 0.1 specification

## Terms and representation

`Schema[A, B]` is the only executable cognitive entity. Its canonical JSON
object contains `name`, `input`, `output`, `body`, typed declarations,
predictions, invariants, falsifiers, provenance, and complexity metadata.
Objects use lexicographically sorted keys, compact separators, UTF-8, finite
JSON values, and ordered arrays. SHA-256 of those bytes is schema identity;
display names carry no authority.

Types are recursively serialized as `{kind, args, name}`. Version 0.1 defines:

```text
Primitive(name)
Product(A, B) | Sum(A, B) | Optional(A) | Sequence(A) | Set(A)
Relation(A, B) | SchemaType(A, B) | ReifiedSchemaType(A, B)
Proposition
```

The surface grammar is intentionally a serialization grammar, not executable
Python:

```text
schema ::= JSON object matching Schema
node   ::= {"op": string, "args": [node...], "value": JSON?}
```

## Implemented morphisms and semantics

| Construct | Signature | Deterministic semantics | Base cost |
|---|---|---|---:|
| `identity[A]` | `A -> A` | return input | 1 |
| `primitive[p]` | registry signature | invoke audited pure function | registry |
| `compose(f,g)` | `A->B, B->C => A->C` | `g(f(x))` | 1 |
| `parallel(f,g)` | `A->B, C->D => A×C->B×D` | `(f(x),g(y))` | 1 |
| `pair(f,g)` | `A->B, A->C => A->B×C` | `(f(x),g(x))` | 1 |
| `project[i]` | `A×B -> A or B` | tuple projection | 1 |
| `constant[v:T]` | `A -> T` | return canonical value | 1 + value length |
| `quote(f)` | `Unit -> ReifiedSchema[A,B]` | return immutable AST | 2 |
| `eval[A,B]` | `ReifiedSchema[A,B]×A -> B` | type-check then interpret | 3 |
| `guard(p,f)` | `A->Prop, A->B => A->Optional[B]` | execute iff true | 2 |
| `choose(p,f,g)` | `A->Prop, A->B, A->B => A->B` | selected branch | 2 |
| `observe(f)` | `A->B => A->B` | execute grounded schema and emit observation event | 2 |
| `predict(f)` | `A->B => A->B` | execute causal schema and emit prediction event | 2 |
| `compare[A]` | `A×A -> Proposition` | canonical equality | 2 |
| `evidence_update` | `Evidence×Proposition -> Evidence` | increment evidence and Laplace confidence | 3 |

Every node is validated before execution. Type-invalid composition, unknown
primitives, malformed values, and revoked schemas fail closed. Complexity is
the sum of node costs, canonical constant/metadata sizes, declarations, and
audited primitive costs; opaque strings cannot hide free executable behavior.

## Audited S0 registry

The initial registry contains generic operations only:

- `observation_difference : Product[Frame,Frame] -> FrameDelta`
- `action_conditioned_transition : Product[FrameDelta,ActionId] -> Transition`
- `transition_prediction : Transition -> FrameDelta`
- `delta_is_empty : FrameDelta -> Proposition`
- `select_first_legal : LegalActions -> ActionId`
- `context_action_prediction : Product[Context,ActionId] -> PredictedResult`
- `transition_property : Transition -> PredictedResult`

Each declaration records a justification, genericity statement, signature,
cost, and pure implementation. New native primitives require firewall review
and closure comparison.

## Causal schemas, diagrams, rewrites, and failures

`Context × Action -> PredictedResult` is an ordinary schema. A diagram stores
typed paths and expected equalities. Evaluation compares canonical outputs; a
disagreement is a structured `DiagramViolation`. A rewrite stores old/new
schema hashes, reason, and declared regression cases. It is admissible only if
the new schema type matches and all cases preserve canonical outputs.

Evidence is the immutable tuple
`(attempts, confirmations, failures, confidence)`. The interpreter computes the
next tuple purely; only `MindCoordinator.commit_evidence` may install it after
verifying that it exactly matches the current record and comparison result.

## Reserved long-term catalogue

The following names are reserved by the research language but are not claimed
as implemented in 0.1: sum branching beyond `choose`, repeat,
`bounded_repeat`, fold, map, filter, bind, epistemic credit/blame,
specialize/generalize/factor/merge/split/abstract/compress/revoke operations,
diagram transport, and automatic grounding/regrounding. Adding one requires a
signature, validation rule, deterministic semantics, serialization, cost, and
tests before the version is incremented.

## Validation and firewall

Schemas cannot contain game/level identifiers, full-frame hashes,
frame-conditioned action scripts, opaque code, future observations, evaluation
metadata, or model calls. Metadata participates in validation and complexity.
The engine supplies only current observations and legal actions.
