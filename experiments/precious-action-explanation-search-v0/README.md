# Precious Action Explanation Search v0

This is the eight-hour causal repair of `pcw-v1-16-qwen-executor-v0`.
It tests whether explanation-space search in a separate procedural Qwen context
saves an ARC action, and whether bounded Python improves that same worker beyond
an otherwise matched verbal Executor.

The governing rule is:

> Free internal computation is cheap; real actions are precious.

The experiment keeps the frozen protocol:

- **A:** exact frozen PCW v1.16. Its candidate is used only in offline matched
  counterfactual evaluation.
- **B:** frozen PCW state plus an isolated verbal QwenExecutor context.
- **C:** identical to B, with the frozen bounded `run_analysis(code)` surface.

In B/C, QwenExecutor is the only worker allowed to propose a concrete legal ARC
action. Semantic Qwen supplies hypotheses and revisions. R2 supplies grounding,
predictions, contradictions, evidence, and control-relevant constraints. The
arbiter validates one Executor proposal and remains the only action-commit
authority.

The new experiment does not rerun B/C from an empty initial state. It selects a
history-bearing boundary mechanically from the exact frozen v1.16 `ar25` trace,
runs B and C from the identical immutable snapshot, and replays each selected
primitive action from the exact same environment prefix.

See `PLAN.md` for the preregistration, `INSIGHT_SOURCE_MAP.md` for research
provenance, `CHECKPOINTS.md` for the append-only work log, and `INSIGHTS.md` for
observations and interpretations generated during the run.

The completed v0 is documented in `results.md`. Earlier qualification attempts
were inconclusive and remain immutable. The final matched specimen engaged both
treatments and replayed A/B/C exactly, but found no B>A, C>A, or C>B qualifying
gain at the preregistered decision boundary.
