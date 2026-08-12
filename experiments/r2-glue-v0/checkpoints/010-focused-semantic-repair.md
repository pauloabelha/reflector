# Checkpoint 010: focused semantic repair

Time: 2026-08-12

## Failure

On explicit semantic failure, ordinary turns still asked local Qwen to
regenerate several independent products from roughly 8.6k prompt tokens. DC22
showed repeated failed goal proposals and stale scratchpad state.

## Repair

An evidenced-failure turn now uses `focused-semantic-revision-v0`:

- exact causal images, the prior five-field state, latest settlement, and R2
  failure evidence remain available;
- unrelated sparse-cut objects and output products are omitted from transport;
- aliases, citations, and abductive compositions are empty generation fields;
- prior compiled action aliases are preserved independently by the compiler;
- Qwen may revise, replace, or abstain from a goal proposal;
- R2 retains exclusive grounding, measurement, and action authority;
- a post-action null-history assertion is rejected generically.

## Evidence

- Ordinary turn: 30.8k characters / 8,610 prompt tokens.
- Focused turns: 15.35–15.93k characters / 4,843–5,102 prompt tokens.
- Two insufficient revisions were rejected.
- The next revision acknowledged prior state and current displacement.
- Its repeated alignment proposal was retired independently.
- The durable goal proposal set became empty; an existing cited alias survived.
- 137 focused tests pass.
- The full suite has 249 passes and one unchanged missing historical artifact.

This verifies semantic-loop repair and memory separation, not DC22 completion,
score gain, or general ARC competence.
