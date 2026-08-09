# Parallel Cognitive Workspace v1.3 — ar25 replacement gate

v1.2 terminated safely before its second Qwen call because the mandatory
lossless ambiguity unit cost 2,979 frontier units and the frozen balanced
budget was 2,400. Qwen therefore never received the new criticism. This
replacement changes only context feasibility and failure observability.

## Frozen changes from v1.2

- Balanced frontier budget: 4,000 units.
- The preserved v1.2 action-8 state was measured at all candidate budgets.
  At 4,000, the 3,630-unit cut includes the complete ambiguity unit and both
  durable expansion/focus roots with none deferred.
- Estimated actual prompt is about 8,236 tokens, leaving about 5,148 tokens of
  the 16,384-token window after reserving the full 3,000-token completion.
- The exact production-profile budget is now covered by a feasibility test.
- Failed jobs atomically mark their progress document `failed` with the typed
  error while retaining the last committed action and graph metrics.

No schema vocabulary, prompt, grounding rule, controller policy, action rule,
Qwen model, trigger, or semantic compression rule changes from v1.2.

## Run and verdict

- Fresh paired `ar25`, balanced profile, at most 25 actions per arm.
- Qwen calls only at action boundaries 0, 8, and 16.
- The pass chain and stop rules are exactly those in `V1_2_AR25_GATE.md`.
- No in-run repair or fourth call. Held-out games remain paused on failure.

