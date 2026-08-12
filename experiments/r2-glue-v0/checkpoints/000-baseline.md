# Checkpoint 000: verified baseline and first seam

Time: 2026-08-12T02:42:48Z

## Repository evidence

- `main` and `planner` diverged after `4247804`.
- `main` contained the R2.2 architecture report; `planner` contained Goal
  Prospect, CAE, and the repaired live lifecycle.
- They were merged without including the original worktree's pre-existing
  experiment deletions or untracked `artifacts/` and `insights/` trees.
- Focused tests passed: 123/123.
- Merge commit `75600da` was pushed to `origin/main`.
- `glue` was created directly from `75600da`.

## Live evidence inherited from the baseline

At the inspected AR25 boundary:

- Qwen retained ALIGN/CONTACT proposals over `fit_residual`;
- R2 reported no active grounded verb, no mechanism, and no planner route;
- CAE correctly refuted a seven-member identity after breakaway;
- CAE retained a new six-member translation candidate with one support;
- the current action remained an information probe;
- repeated semantic revisions were rejected by the scratchpad revision gate.

This supports “CAE evidence bookkeeping works at this boundary.” It does not
support “R2 understands the AR25 goal,” “the six-member factor is correct,” or
“CAE improves control.”

## Code-level seam

The semantic prompt says FIT should use `fit_residual`; the response schema
restricts observables and role predicates to closed enums; abductive
compositions can only reference already-stable schema IDs. R2 computes a
`hole_count`, but negative-space regions are not first-class bindings and Qwen
cannot propose a bounded measurement construction over them.

The intervention target is therefore the general proposal/measurement boundary,
not an AR25 behavior rule.
