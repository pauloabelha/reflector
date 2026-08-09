# Parallel Cognitive Workspace v1.8 results

## Outcome

v1.8 is a valid **FAIL**. Enlarging the Qwen context removed every v1.7
transport and capacity failure, but did not produce the missing
evidence-to-revision-to-control chain.

| Arm | Level 1 | Actions | Exact replay | Final digest |
|---|---:|---:|---:|---|
| R2 only | no | 48 | yes | `8b040597...de08a` |
| Shared live Qwen | no | 48 | yes | `232e1bfe...d789` |

All validity gates passed: same fresh initial observation, exact factual and
empty counterfactual replay, valid context, complete Qwen transport, and zero
support-authority violations.

## What the larger context proved

- All four scheduled Qwen calls completed and compiled.
- Maximum prompt usage was 15,129 tokens, well inside the 24,576-token window.
- The shared arm created two grounded Qwen-to-R2 pickups.
- R2 emitted prospective predictions, changed four exploratory actions, and
  received one environment support judgment.

Thus v1.7's truncated/HTTP-400 responses were genuinely a serving-capacity
problem, and the context-only repair solved that problem.

## Why the cognitive loop still failed

The protocol creates a `revision_task` only from an explicit structured
criticism of an ambiguous or rejected grounding. In this run Qwen's live
proposal grounded uniquely. R2 probed it and the environment returned evidence,
but that evidence did not itself create a revision task. Later Qwen turns were
therefore treated as bootstrap proposal turns; they produced repeats or other
initial proposals rather than an evidence-citing revision of the tested schema.

The final causal metrics are correspondingly empty where the breakthrough gate
matters: zero Qwen revision schemas, zero evidence-citing revision derivations,
zero confirmed revised bindings, zero revised control decisions, and zero
same-state counterfactual branches.

The next version must make prospective evidence a first-class exact revision
unit, reserve the intended confirmation-probe slot, and give Qwen a compact
semantic evidence packet rather than payload-free event addresses. Increasing
context again would not address the demonstrated failure.
