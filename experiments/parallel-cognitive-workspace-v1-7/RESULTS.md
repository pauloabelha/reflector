# Parallel Cognitive Workspace v1.7 results

## Outcome

The preregistered binary verdict is **INVALID**, not a scientific failure. The run violated the frozen context and all-due-Qwen-call transport/compilation gates.

| Arm | Level 1 | Actions | Exact replay | Final digest |
|---|---:|---:|---:|---|
| R2 only | no | 48 | yes | `8b040597...de08a` |
| Shared live Qwen | no | 48 | yes | `8b040597...de08a` |

The shared arm therefore produced no task gain and did not reproduce the historical 17-action solve.

## What worked

The central prospective loop became executable:

1. Qwen generated a live, non-frozen schema: `SameOutline(?a,?b) -> Decrease TranslationAlignmentResidual(?a,?b)`.
2. R2 grounded it without collapsing ambiguity, retaining three distinct effect-pair hypotheses.
3. R2 selected actions that genuinely discriminated among their predictions.
4. The environment adjudicated predictions explicitly in the shared graph: 39 supported, 2 refuted.
5. One grounded Qwen-to-R2 pickup was durable, support authority violations were zero, and the shared action sequence diverged from fallback four times during probing.

This is stronger than transport-only coexistence: Qwen's live object caused R2 to construct hypotheses, intervene, and collect prospective evidence.

## What did not work

Qwen never completed the evidence-driven revision step:

- Four calls were scheduled and durably integrated, but only the initial response compiled.
- The first evidence-bearing follow-up produced malformed/non-JSON output.
- The final two calls received HTTP 400 responses as context grew beyond safe capacity.
- Maximum prompt usage reached 16,107 tokens; with the frozen 2,048-token completion reserve this cannot fit the 16,384-token context window.
- Consequently there were no Qwen revision schemas, no prospectively confirmed revised binding, no revised-schema control action, and no favorable same-state counterfactual.

The four changed actions were probes, not evidence-backed revised control. Both arms returned to the same final state and neither solved the level.

## Interpretation

The result is **architecturally promising but solver-unproven**. R2 can now actively test a live Qwen hypothesis and return exact evidence through the common workspace. The present bottleneck is the evidence-bearing Qwen turn: its lossless causal context must fit reliably, and structured generation must survive that turn. A successor experiment should change those generic interface constraints in a new version; v1.7 should remain frozen as the checkpoint showing the first complete proposal-to-prospective-evidence path.

Authoritative artifacts are under `artifacts/`; `SUMMARY.json` contains the frozen verdict and both replay-verified arm results.
