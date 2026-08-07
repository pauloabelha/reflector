# Reflector-II inspector

Start the localhost-only, dependency-free inspector from the repository root:

```bash
PYTHONPATH=src python3 inspect/server.py --port 8765
```

Open <http://127.0.0.1:8765/inspect/>. Select one of the 25 local public ARC games
to load and analyze its first frame. The interface can also load PNG/JPEG/WebP/GIF pixel
art. Uploaded images are reduced to at most 96×96 and 32
deterministic colors in the browser before their integer grid is sent locally.

The backend runs `perceive_grid` and `Runtime.observe` from the real Phase-1
implementation. The graph, candidate/established/promoted state, concept cards,
reusable-candidate labels, acyclic
decomposition DAGs, child/owner variable interfaces, bindings, evidence,
provenance, frontiers, timings, memory estimates, and budget events are
projections of that result. The inspector does not choose actions or mutate an
ARC environment.

The graph drawer also shows LLM-authored natural-language readings for each
runtime predicate. These come only from
`assignments/predicate-labels.json`. The inspector loads them after runtime
analysis and labels them explicitly as external annotations; they are never
passed to `Runtime`, included in schema identity or evidence, or stored as
Reflector knowledge. Per-game whole-schema labels use the same one-way display
boundary in `<game>.schema-labels.json`.

The server binds to `127.0.0.1` by default and has no external dependencies.

The inspector uses a larger, explicitly read-only exploration budget than the
normal runtime: up to 2,048 bindings per schema, 2,048 active schemas, 4,096
composition proposals, and sixteen bounded composition rounds. It also adds one
generic `Color(entity, value)`
pattern per palette value to its isolated graph so visually distinct groups can
be inspected. These are nominal value schemas, not color names; any names such
as “green” or “yellow” remain external annotations in the inspector.
