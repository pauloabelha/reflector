# Runtime semantics

Interpretation is call-by-value and deterministic. Inputs, ASTs, Minds,
candidate tasks, results, and trace events are immutable values. The checker
derives a unique morphism type before a node may run. Primitive implementations
are pure with respect to runtime state. Canonical JSON equality defines
observable equality for diagrams and regression cases.

Only the coordinator owns the current Mind. Worker results are advisory values;
they are fully collected, sorted, validated, and reduced in a single explicit
transaction. A missing or failed worker aborts the transaction.

The developmental loop executes `observe`, `predict`, `compare`, and
`evidence_update` as ordinary typed nodes. A causal prediction is made before
the environment transition. Comparison occurs only after the actual
transition. Evidence and rewrite candidate evaluation are pure; coordinator
transactions validate revision, identity, types, firewall, and derived evidence
before returning a new immutable Mind.
