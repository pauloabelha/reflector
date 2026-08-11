# R2.1 schema-first substrate

## Purpose

R2.1 makes the reusable schema the primary cognitive object. It does not add
ARC roles or a new game solver. It operates on opaque, typed support handles
and environment-authored relational facts supplied by an adapter.

```text
grounded supports → relation facts → schema retrieval → competing bindings
  → shadows → environment settlement → support / accommodation
```

Control, goal inference and Qwen are later clients of this substrate.

## Recursive binding workspace

The current world of the fitter is not the frame alone. `BindingWorkspace`
contains typed `WorkspaceAtom`s. Schema_0 bindings create the first atoms from
raw `GroundSupport`s. Every complete higher binding creates another atom whose
type is the schema's advertised `output_type`. That atom may immediately fill
a port of another retrieved schema.

```text
GroundSupport
→ Schema_0 binding : region-binding
→ relational binding : pair-binding
→ higher binding : configuration-binding
→ ...
```

Every atom carries the union of environment evidence in its derivational
ancestry, so high-level cognition remains grounded without touching pixels
directly. Partial bindings remain workspace objects but do not masquerade as
completed atoms; their open constraints generate shadows.

`RecursiveSchemaFitter` performs semi-naive closure. A newly added atom only
activates schemas indexed for one of its compatible port types, and every new
derivation includes an atom from the delta queue. A fact delta only revisits
partials whose open predicates occur in that delta. Structural IDs deduplicate
old consequences.

`max_depth_increment` is explicitly a per-cycle budget. It is not an ontology
level limit. Later cycles can continue from any existing depth.

## Data model

| Object | Durable meaning | May change empirical support? |
| --- | --- | --- |
| `Schema` | reusable typed definition DAG | only through cited environment facts |
| `Binding` | partial, episode-specific port assignment | only through cited environment facts |
| `Shadow` | an unobserved required relation/port | never directly |
| `GroundFact` | environment-authored relation over support IDs | is evidence |
| `Transformation` | oriented schema signature (`before`, `intervention`, `after`) | no; it is a definition |

`Schema` IDs are content addresses over canonical port types, relation rows,
component IDs, and kind. The definition graph rejects cycles. A composition
retains component schema IDs and its binding derivation, so it can later be
used atomically without losing decomposition.

Definitions with at most eight ports are exactly canonicalized modulo
type-preserving alpha-renaming before hashing. Larger definitions have a
deterministic fallback and should normally be decomposed into smaller DAGs.

`Binding` IDs are content addresses over schema ID, assignment map, and the
set of satisfied/open constraints. Open ports and open constraints are stored
explicitly. A partial binding is therefore a legitimate state, not a failed
complete binding.

`workspace_object()` projects each data type as a distinct shared-workspace
object (`schema_definition`, `schema_binding`, `schema_shadow`) with stable
identity and dependency/derivation IDs. A Qwen proposal can be represented by
the same shape but starts with zero support; it may affect salience only.

## Fitting algorithm

```text
update(facts):
  candidates := predicate/type indexed retrieval(facts, retrieval_budget)
  parallel for schema in candidates:
      fit schema constraints against facts by bounded relational joins
      retain every compatible partial branch
  parallel for active partial binding:
      seed the same bounded join with its existing assignments
      retain every compatible extension
  keep top-k bindings by salience in the active frontier
  for each active partial binding:
      create shadows for exact open constraints
  mutate durable support only from cited GroundFacts
```

The engine does not scan every schema. `SchemaStore` keeps inverted indexes by
predicate and port type; retrieval only scores the union of matching index
buckets. The active frontier is bounded, but durable definitions and evidence
are not deleted when they become dormant.

Constraint joins evaluate the most selective available predicate first.
`EquivalenceIndex` represents invariant/signature classes through linear
membership rather than materializing every pairwise `Same` relation.

## Canonicalization and invention

A local relational motif is canonicalized by replacing grounded entity IDs with
first-occurrence typed port aliases. For example, two episodes with different
support IDs both reduce to:

```text
SameOutline(p0:figure, p1:figure)
DifferentFill(p0:figure, p1:figure)
```

The canonical motif content-addresses to one `Schema`. `SchemaInventor`
records the distinct observation contexts that instantiated it. The current
minimal promotion policy is deliberately conservative and measurable:

```text
promote iff the same canonical relational motif appears in >= 2 contexts
```

The promoted schema begins as a reusable hypothesis. Its support is then
incremented only by environment evidence cited by later bindings and reified
shadows. Future versions can add compression, cross-context prediction,
invariance and causal usefulness to promotion scoring without changing the
representation.

## Shadows and settlement

For every unmatched relation constraint, R2.1 creates a `Shadow` containing
the required predicate, grounded arguments already known, and genuinely open
ports. It is neither a fact nor support.

```text
SameOutline(c3,c4) observed
DifferentFill(c3,c4) required by a partial binding
→ Shadow(DifferentFill(c3,c4))
```

A matching later `GroundFact` reifies it. Refutation requires an explicit
adapter-supplied contradictory predicate. Non-observation does not refute a
shadow.

## Transformations and category-inspired composition

`Transformation` is an oriented view of an ordinary schema with ports named
`before`, `intervention`, and `after`. Static and temporal schemas therefore
use exactly the same fitting and partial-completion mechanism. The helper
`compose_transformations` checks that one transformation's after-port feeds a
second's before-port; the composed definition is still represented by normal
schema composition. This is a computational composition check, not a claim of
literal category-theoretic machinery or Kan extensions.

## Epistemic invariants

1. Schema definition != binding.
2. Binding != evidence.
3. Shadow != observed fact.
4. Salience != support.
5. Only `GroundFact.evidence_id` changes empirical support.
6. Partial/competing bindings are preserved within the bounded frontier.
7. Definition DAGs are acyclic; a later association graph may be cyclic.
8. No game/action/role semantics are built into this module.
