# Parallel Cognitive Workspace v1.20

## Architectural repair

v1.18 and v1.19 were both `INVALID` before calibration because a single
frontier number incorrectly served two purposes:

1. how much optional salience-ranked material a worker may attend to; and
2. whether every live competing binding and its exact causal dependencies may
   remain visible at all.

The required exact unit varied across fresh runs (9,843 and 10,841), so tuning
one fixed cut to the previous trace is not a robust solution.

v1.20 freezes a two-tier policy:

- optional attention budget: 6,400 units;
- mandatory exact frontier ceiling: 14,000 units.

Frontier construction first uses 6,400. If and only if it reports that the
mandatory dependency-closed unit does not fit, construction retries at the
reported exact required size. It may not admit optional fill during that
retry. A required unit above 14,000 is a typed `INVALID` capacity outcome.

This policy applies symmetrically to R2's cut and Qwen's turn. The authoritative
graph remains complete. No live alternative, causal dependency, relation
packet, or grounding is summarized away. The 14,000 ceiling leaves a
conservative envelope beneath the frozen 24,576 context with 3,072 output
tokens reserved.

Before each real cognitive completion, an admission-only request sends the
exact same multimodal prompt and response schema with `max_tokens=1`. Its
semantic output is discarded, while the serving stack's actual prompt count is
persisted with the real response. The real request is sent only when prompt +
3,072 reserve fits within 24,576 with an additional 512-token safety margin.
This counts vision and chat-template tokens exactly.

## Experiment

Rerun both wa30 development arms from fresh empty workspaces. Everything from
v1.18's calibration experiment remains unchanged: 64 actions, Qwen model and
cognitive schedule, controller, DSL/compiler, typed probes, environment-only support,
evidence return, replay, counterfactuals, and verdict.

The inherited calibration gate remains authoritative. No outcome from v1.18
or v1.19 is reused as cognition or control state.
