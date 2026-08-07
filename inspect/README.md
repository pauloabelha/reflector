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

The server binds to `127.0.0.1` by default and has no external dependencies.
