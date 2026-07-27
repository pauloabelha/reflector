# Architecture

Reflector has one inference core and several consumers.

```text
reflector.SymbolicPolicy
  ├── official Agent adapter ── official Swarm/Arcade ── local runs
  ├── generated Kaggle overlay ── official starter ── Kaggle gateway
  ├── experiment runner (future)
  ├── population evaluator (future)
  └── replay API/UI (future)
```

`Observation` and `Decision` are immutable protocol values. The baseline policy
uses integer action identifiers so the core has no dependency on the ARC
toolkit. The adapter is responsible only for translating between these values
and official `FrameData`/`GameAction` objects.

The Kaggle artifact is an overlay, not a fork. It contains the shared package,
the thin adapter, and a minimal agent registry. The notebook extracts those
files over the competition-provided official starter and invokes its `main.py`.

Development-only systems will depend inward on the symbolic package. The
symbolic package must never depend outward on an evolver, LLM, trace analyzer,
SQLite store, API server, or frontend. `tests/integration/test_kaggle_contract.py`
enforces the current inference closure.

The next vertical slice may add typed items, observations, transitions, and
schemas inside `reflector/`, but only serializable state that can be created and
used under the same Kaggle process belongs there.
