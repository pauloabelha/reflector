# Metadata

- Name: Prospective Context Spinoff Control
- Slug: `prospective-context-spinoff-control`
- Created: `2026-08-08T01:07:49Z`
- Repository: `/home/pauloabelha/reflector2`
- Status: complete; success gate passed
- Source recording SHA-256:
  `b7859f018249af517cb5052ce27e22c08dde76ca635e0e3cb2703bbe23bfb102`
- Measured artifacts: `summary.json`, `trace.json`

## Initiating prompt

> Implement the next minimal Reflector-II experiment: **Prospective Context
> Spinoff Control**.
>
> Goal: test whether R2 can turn ambiguity in an existing causal schema into a
> context-specialized child schema that **changes an online action choice in a
> real ARC game**.
>
> Use the current R2 multi-directional schema machinery and existing real-game
> recordings/code. Do not add semantic labels such as `wall`, `mode`,
> `controlled_object`, `key`, etc. Do not add options, Qwen, new planning
> machinery, or game-specific branches.
>
> Protocol:
>
> * Pick one real ARC game/level where baseline Reflector already makes
>   meaningful progress but encounters repeated action/effect ambiguity.
> * When one schema yields multiple plausible action or successor shadows,
>   inspect only **predecessor-visible, currently active schema bindings and
>   relations**.
> * Find a bounded context condition whose presence/absence materially
>   separates the competing outcomes.
> * Preserve the general parent schema and create a **context-specialized
>   child**.
> * Let that child immediately affect the ranking of the **next prospective
>   action**.
> * Execute the action and record whether its predicted shadow is
>   reified/refuted.
>
> The key causal chain must be visible in the trace:
>
> `ambiguity → discovered context → parent→child spinoff → changed action ranking → prospective outcome`
>
> Compare against the same game/level without context spinoffs.
>
> Success requires at least one case where R2 autonomously discovers a
> non-game-specific predecessor context, changes the top-ranked action relative
> to baseline, and improves successor prediction/progress or avoids a baseline
> mistake.
>
> Report:
>
> * chosen game/level and why it is diagnostic;
> * exact parent and child schemas;
> * context relation discovered;
> * before/after action rankings;
> * prospective predictions and outcomes;
> * action/progress difference vs baseline;
> * whether the mechanism looks generic enough to justify a 25-game run.
>
> Keep it brutally minimal. The purpose is not architecture expansion; it is
> to test the shortest plausible bridge from R2’s current
> **candidate-set-but-wrong-ranking** gap to actual ARC control.
