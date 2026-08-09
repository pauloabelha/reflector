# Parallel Cognitive Workspace v1.10 status

## 2026-08-09 — replacement preflight

- v1.9 was preserved as implementation `INVALID`; its artifacts are excluded.
- This version changes only the graph criticism vocabulary and experiment
  identity/artifact root.
- No v1.10 environment has been opened and no v1.10 Qwen request has been made.
- Pending before launch: real-reducer replay test, full v1.9 regression suite,
  dry-run manifest, resident-server verification, and a git checkpoint.

## 2026-08-09 — implementation freeze ready

- The authoritative v1.4 graph reducer now admits exactly the new
  `prospective-evidence-return` status; no other reducer or control semantics
  changed.
- A real-reducer regression proves ingestion at support zero, target/evidence
  dependency preservation, and canonical event replay.
- The complete v1.9 + v1.10 suite passes (`17 passed`), as do module compilation,
  wrapper dry-run/manifest construction, and `git diff --check`.
- Configuration remains unchanged except experiment/protocol identity. The
  resident Qwen server/model/context were already verified immediately before
  the v1.9 run and remain resident; they will be checked once more before reset.
- Live scientific and causal gates remain entirely untested in v1.10. The next
  action is one new fresh paired run; no v1.9 artifact is eligible for loading.
