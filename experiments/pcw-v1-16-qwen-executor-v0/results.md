# Results

## Decisive run

The preregistered run completed under manifest
`14ebed7872bba10980b79208f0666f437dae576683f021dde2df7754bb2ffb01`.
The frozen Executor primitive set was
`executor-generic-primitives-v0.1`, source hash
`2950ff439a59f80567d27ed3d2ac1710c5b25a8de010c6e5a8022e53583a934d`.

| Arm | Actions | Levels | Stop | Executor calls | Semantic calls | Python calls | Replay |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| A — frozen PCW v1.16 | 38 | 1 | first level completed | 0 | 4 | 0 | exact |
| B — verbal Executor | 0 | 0 | Executor abstained | 2 | 1 | 0 | exact |
| C — Python available | 0 | 0 | Executor abstained | 2 | 1 | 0 | exact |

All arms began from digest
`8c9c38b5c049817e37ea6525b513983e3628a3f1224df5eafb3146175bb2a51b`.
All had zero support-authority violations. Arms B/C emitted no
`ActionCommit`, `ActionPending`, or environment transition, so no fallback or
competing PCW policy spent an action.

## Failure funnel

Arm B returned two ranked legal candidates (`ACTION_7`, `ACTION_5`) but chose
the structured abstention reason `no_legal_action`. The inconsistency was not
converted into an action: the sole-policy/arbiter boundary stopped the episode.
Its failure funnel is `EXECUTOR_ABSTAINED: 1`.

Arm C returned one ranked candidate (`ACTION_1`) but also chose
`no_legal_action`. Although it emitted a bounded 20-line code value, it marked
the analysis mode `verbal`; the sandbox therefore correctly did not execute
the code. It also emitted the literal string `"None"` as a missing-operation
diagnostic. Its funnel is:

```text
EXECUTOR_ABSTAINED: 1
NO_PROCEDURAL_COMPUTATION: 1
SNAPSHOT_OR_TOOLING_INSUFFICIENT: 1
```

This is a tool-uptake failure, not evidence about Python computation quality.
The exact computations and proposals are retained as content-addressed blobs
in each arm workspace.

## Verdicts

- **Dedicated procedural context, B > A:** not supported. A completed the
  level; B spent zero actions and made no progress.
- **Python availability, C > B:** not supported by intention-to-treat outcome;
  both made zero progress. The code-mediated mechanism effect is **not
  identified**, because C did not execute Python in the decisive call.
- **Authority architecture:** supported mechanically. Executor was the sole
  concrete proposal source in B/C, arbiter remained sole commit authority,
  and no action escaped an abstention or failed computation.
- **Counterfactuals:** no B/C first divergence exists because neither arm
  committed an action. Arm A retains its frozen eight favorable, exact
  one-step counterfactuals; they were not used as a live competing policy.

The negative result is frozen as observed. No primitive was added, no
abstention was overridden, and no post-hoc rerun was used to manufacture tool
engagement.

## Controls

Fixture controls passed, including frozen-source hashes, worker isolation,
semantic/R2 action-authority exclusions, arbiter authority, sandbox bounds,
and environment-only empirical support. Thirty-two frozen v1.14-v1.16 plus
Executor-v0 regression tests passed.
