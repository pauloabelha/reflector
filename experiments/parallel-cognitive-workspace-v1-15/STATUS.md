# Parallel Cognitive Workspace v1.15 status

## 2026-08-09 — freeze ready

- v1.14 is preserved as INVALID after its first confirmed revised-control
  transition because an unchanged probe packet attempted to reuse a criticism
  identity with a newer grounding payload.
- v1.15 changes only that criticism lifecycle: unchanged packet means reuse;
  novel packet means a new immutable criticism.
- No v1.15 ARC environment has been opened and no fresh-workspace Qwen request
  made.
- The preserved v1.14 action-25 prefix reproduces the collision exactly. With
  the v1.15 adapter installed, the unchanged packet is recognized by its frozen
  criticism key and the renderer is not called; the already-committed control
  evidence remains present in the graph.
- A synthetic additional probe-evidence fixture changes the packet/key and
  proves that a genuinely novel criticism is still created. Mixed-schema
  filtering and idempotent installation are covered.
- Twenty-two v1.14/v1.15 tests pass. Dry-run manifest construction, Python
  compilation, and `git diff --check` pass. No controller, Qwen prompt, schema,
  action budget, or causal gate changed.
