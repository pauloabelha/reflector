# Parallel Cognitive Workspace v1.6 status

## 2026-08-09 — correction preflight

- v1.5 settings unchanged.
- Ambiguity diagnostics cannot overwrite live controller state.
- Fresh artifacts only; live run not started.

## 2026-08-09 — terminal result

- Binary verdict: `INVALID` (mandatory-context infeasibility at action 12).
- The live causal prefix strengthened: 3 live alternative bindings, 72 durable
  predictions, 12 exact environment supports, and one grounded Qwen→R2 pickup.
- Qwen turn two was not sent: mandatory closure cost 9,153 exceeded 6,400.
- Exact cause: each binding duplicated the complete ambiguity witness already
  stored once in its exact structured-criticism object. v1.7 replaces those
  copies with compact situated binding facts while keeping the witness exact
  and addressable once.



## 2026-08-09 10:46:04 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- FAILED `generic_prospective/ar25/shared_live_qwen`: FrontierBudgetError: frontier budget 6400 is below mandatory closure cost 9153.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=48, Q→R grounded=0, replay=True.
