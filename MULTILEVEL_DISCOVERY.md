# Bounded multi-level discovery

Reflector-II discovers schemas by bounded closure over active evidence. It does
not contain a rule for a particular ARC game, L-shape, colour, or pair label.

## Levels

The current default coordinator has four composition rounds and a total budget
of 256 composition proposals per observation. It preserves the sparse active
workspace limits (`256` nodes and `1024` edges) while allowing an observation
to reach beyond a one-step conjunction.

The final 64 proposal slots are reserved for **generic relational closure**.
For a depth-zero relation binding between two typed entities, the coordinator:

1. finds one existing non-relational descriptor for each endpoint;
2. groups all primitive relation atoms that bind the same endpoint pair;
3. creates a canonical conjunction with those relation atoms and both child
   descriptors;
4. records all children as distinct DAG occurrences with their variable
   interfaces.

This is relation-arity driven, not predicate-name driven. The same path works
for containment, matching outlines, comparative attributes, or another binary
relation supplied by generic perception.

## `ar25` oracle

The raw first frame has three colour-agnostic figures with one outline class
under translation, rotation, and reflection. The generic perceptual facts are:

- three `SameOutline` bindings;
- two `DifferentInteriorContrast` bindings;
- one `SameInteriorContrast` binding.

The discovered hierarchy contains a level-1 figure descriptor:

```text
Kind(x, Figure) ∧ OutlineForm(x, outline)
```

and two depth-2 relational schemas:

```text
SameOutline(a, b) ∧ DifferentInteriorContrast(a, b)
∧ LFigure(a) ∧ LFigure(b)    # two bindings

SameOutline(a, b) ∧ SameInteriorContrast(a, b)
∧ LFigure(a) ∧ LFigure(b)    # one binding
```

Each pair DAG has two occurrences of the same level-1 figure schema, one
bound to each endpoint. The phrase `LFigure` is explanatory shorthand; the
stored schema uses only the canonical relational body and hash.

## CPU parallelism

An individual observation uses one deterministic coordinator because it
mutates one schema graph. Independent observations are process-parallel. The
25-game evaluator defaults to `--workers 0`, using available CPU cores while
returning games in deterministic lexicographic order.

```bash
PYTHONPATH=src python3 -m reflector2.evaluate_first_frames \
  /path/to/one-recording-per-game --expected-games 25 --workers 0
```

On the local 25-frame corpus, 24 worker processes completed the latest audit
in 0.308 seconds of evaluator wall time. Timing is workload- and machine-
dependent, not a throughput guarantee.

## Regression evidence

The test suite includes:

- generic reflected-outline / internal-contrast discovery without ARC data;
- a cap regression for pair generation;
- no pair-schema installation for an ordinary unpaired frame;
- the `ar25` three-pair perception witness;
- the `ar25` depth-2 two-child-occurrence oracle;
- the all-25 bounded first-frame audit.
