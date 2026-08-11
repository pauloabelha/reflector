# Parallel Cognitive Workspace v1.8 status

## 2026-08-09 — context-capacity preflight

- v1.7 scientific settings unchanged except Qwen context window.
- Required server context: 24,576 tokens.
- Fresh artifacts only; live run not started.

## 2026-08-09 11:19:48 — terminal result

- Both arms completed 48 actions with exact replay and zero job failures.
- Binary verdict: `FAIL` (all validity gates passed).
- Neither arm completed level 1; the shared arm ended at a different final digest but without task gain.
- All four Qwen calls transported and compiled. Maximum prompt usage was 15,129 of 24,576 tokens, so v1.7's context failure was removed.
- Qwen created two grounded Qwen-to-R2 pickups and changed four exploratory actions. One prospective prediction received environment support.
- No evidence-driven non-alpha revision was created, no revised binding was confirmed, and no revised-schema control or counterfactual branch occurred.
- Root cause: a uniquely grounded live proposal receives prospective evidence but does not create the explicit criticism/revision task required by the Qwen protocol. Evidence remained durable without becoming a semantic revision obligation.


## 2026-08-09 11:11:11 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=48, Q→R grounded=0, replay=True.
- COMPLETE `generic_prospective/ar25/shared_live_qwen`: levels=0, actions=48, Q→R grounded=2, replay=True.
