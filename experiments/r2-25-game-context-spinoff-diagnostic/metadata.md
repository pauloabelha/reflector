# Metadata

- Name: R2 25-Game Context Spinoff Diagnostic
- Slug: `r2-25-game-context-spinoff-diagnostic`
- Created: `2026-08-08T01:17:45Z`
- Repository: `/home/pauloabelha/reflector2`
- Objective attachment:
  `/home/pauloabelha/.codex/attachments/df385276-89a4-42fb-bab5-c4095c52c472/goal-objective.md`
- Status: running

## Initiating prompt

> Scale the successful Reflector-II “Prospective Context Spinoff Control”
> mechanism unchanged to the full fixed 25-game public ARC-AGI-3 cohort.
>
> This is a diagnostic, not a new architecture experiment. Do not tune per game
> and do not add explanations, options, Qwen, semantic labels, game IDs, level
> IDs, coordinates, or handcrafted branches.
>
> Parallelize independently across games using multiprocessing/process workers,
> with a configurable `--workers` argument defaulting sensibly to available
> CPUs. Each game must remain chronologically serial and isolated. Results must
> be deterministic for fixed seeds and identical between `--workers 1` and
> parallel execution.
>
> For each game, replay/evaluate chronologically using predecessor-visible
> information only. On genuine parent ranking ambiguity, search the bounded
> currently active depth-0 binary relation bindings and their presence/absence
> exactly as in the successful `ar25` experiment; learn only from preceding
> evidence; preserve the parent; create a context child; rerank opaque actions;
> prospectively emit and resolve the child shadow when top-1 changes; and run a
> matched no-spinoff control from the identical predecessor wherever possible.
>
> Primary metric: action-changing precision, with “better” defined primarily
> by level/progress and then by a preregistered generic prospective structural
> comparison.
>
> Report the full requested aggregate/per-game, negative-result, calibration,
> concentration, context, timing, and CPU metrics. Produce `summary.json`, one
> trace per game, compact opportunity JSONL/CSV, a Markdown report, exact
> configuration/seeds, and tests for leakage, labels, parent preservation,
> serial/parallel identity, and worker isolation. Include `ar25` as a frozen
> sanity check. End with `PROMOTE`, `CONTINUE-DIAGNOSTIC`, or `REJECT`; do not
> promote from aggregate prediction accuracy alone.

The complete prompt is retained verbatim in the objective attachment named
above.
