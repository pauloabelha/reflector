# Parallel Cognitive Workspace v1.7 status

## 2026-08-09 — normalization preflight

- v1.6 settings unchanged.
- Exact ambiguity witness stored once; bindings store exact candidate facts.
- Fresh artifacts only; live run not started.


## 2026-08-09 10:50:12 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=48, Q→R grounded=0, replay=True.
- COMPLETE `generic_prospective/ar25/shared_live_qwen`: levels=0, actions=48, Q→R grounded=1, replay=True.

## 2026-08-09 10:59:01 — terminal result

- Run completed without job failures; both factual ledgers replay exactly.
- Binary verdict: `INVALID` (`context`, `transport`).
- Neither arm completed level 1. Both stopped at 48 actions and reached the same final digest.
- The live workspace loop made real progress: Qwen proposed one non-frozen schema; R2 preserved three competing grounded bindings, issued discriminating probes, and recorded 39 supported plus 2 refuted prediction objects.
- Four shared-arm actions differed from the scratch fallback, but they were exploratory probes. No evidence-citing Qwen revision compiled, so there was no revised-schema control decision or causal counterfactual branch.
- Qwen call 1 compiled. Call 2 returned a malformed/non-JSON response. Calls 3 and 4 were rejected by the server with HTTP 400 after the rendered context grew too large. Maximum prompt usage was 16,107 tokens before the frozen 2,048-token completion reserve.
- Focused cumulative verification: 19 tests passed; `git diff --check` clean.
