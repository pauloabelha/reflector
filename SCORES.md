# Reflector-II scores

> **Target: Kaggle public score > 1.00.**  Best measured Kaggle public score:
> **0.02**.  Current main solver: **Parallel Cognitive Workspace v1.16**.
> Its verified local result is **ar25 level 1 in 38 actions**, against an
> R2-only control that completed **0 levels in 64 actions**.  The current main
> solver has **not yet been submitted to Kaggle**, so its Kaggle score is
> unknown and must not be reported as 0.02.

Last evidence audit: 2026-08-09.

## Scoreboard

| Record | Result | Status |
|---|---:|---|
| Kaggle target | **> 1.00** | Required breakthrough threshold |
| Best measured Kaggle public submission | **0.02** | Submission `55226491`, older frozen v164 broad policy |
| Later measured Kaggle submission | 0.01 | Submission `55312436`, v168 regression |
| Current main: PCW v1.16 shared R2+Qwen | **ar25 L1 @ 38 actions** | Fresh paired development regression; exact causal gate passed |
| PCW v1.16 R2-only control | ar25 L0 @ 64 actions | Same initial observation; exact replay |
| Broadest public development sweep | **16/25 games reached L1** | Online capability-registry development; not held-out and not current main |
| Sealed capability batch v3 | 0/16 eligible games | Valid negative breadth result; remaining games abstained/errored |

The 0.02 leaderboard score belongs to the older broad-policy submission.  It
is retained as the official external baseline, not attributed to PCW v1.16.
Likewise, the 16/25 development sweep demonstrates that repository mechanisms
can execute many public level-1 solutions, but it does not establish generic
transfer: those games were consumed during development.

## Current winner

The behavioral winner and canonical `main` baseline is
`prospective-control-v1.16`, runnable through `reflector2-workspace`.

| Arm | Game | Levels | Actions | Outcome |
|---|---|---:|---:|---|
| R2-only | ar25 | 0 | 64 | action budget exhausted |
| Shared R2 + Qwen | ar25 | **1** | **38** | first level completed |

The shared arm passed the complete preregistered chain:

```text
ambiguous Qwen proposal
  -> R2 prospective probes
  -> exact environment evidence returned to Qwen
  -> evidence-citing non-alpha Qwen revision
  -> unique R2 grounding
  -> prospective confirmation
  -> changed R2 control
  -> level 1 completion
```

The run recorded four successful Qwen calls, 13 post-revision changed control
decisions, exact factual replay, and eight favorable exact same-state
counterfactual branches.  Support authority, context, transport, initial-state,
and replay gates all passed.  This makes it a real causal result, but still a
single public development-game result.

## Current-main game matrix

`L1@38` means one completed level in 38 actions. `L0@64` means no completed
level at the action cap. `-` means the exact frozen current-main solver has not
produced a valid measured result for that game. Untested cells are never zero.

| Game | PCW v1.16 shared | PCW v1.16 R2-only |
|---|---:|---:|
| ar25 | **L1@38** | L0@64 |
| bp35 | - | - |
| cd82 | - | - |
| cn04 | - | - |
| dc22 | - | - |
| ft09 | - | - |
| g50t | - | - |
| ka59 | - | - |
| lf52 | - | - |
| lp85 | - | - |
| ls20 | - | - |
| m0r0 | - | - |
| r11l | - | - |
| re86 | - | - |
| s5i5 | - | - |
| sb26 | - | - |
| sc25 | - | - |
| sk48 | - | - |
| sp80 | - | - |
| su15 | - | - |
| tn36 | - | - |
| tr87 | - | - |
| tu93 | - | - |
| vc33 | - | - |
| wa30 | - | - |

## Historical public development matrix

This matrix records the broadest exact-replay development sweep,
`online-capability-registry-development-v0`.  It is a capability inventory and
regression target, **not** a held-out score and **not** evidence that the current
main solver reproduces these wins.

| Game | Levels/actions | Exact replay |
|---|---:|:---:|
| ar25 | **L1@27** | yes |
| bp35 | L0@96 | yes |
| cd82 | **L1@22** | yes |
| cn04 | L0@96 | yes |
| dc22 | L0@96 | yes |
| ft09 | **L1@4** | yes |
| g50t | **L1@37** | yes |
| ka59 | **L1@21** | yes |
| lf52 | **L1@44** | yes |
| lp85 | **L1@37** | yes |
| ls20 | **L1@25** | yes |
| m0r0 | **L1@39** | yes |
| r11l | **L1@18** | yes |
| re86 | **L1@30** | yes |
| s5i5 | **L1@34** | yes |
| sb26 | **L1@13** | yes |
| sc25 | L0@96 | yes |
| sk48 | L0@96 | yes |
| sp80 | **L1@14** | yes |
| su15 | L0@96 | yes |
| tn36 | L0@96 | yes |
| tr87 | **L1@64** | yes |
| tu93 | **L1@29** | yes |
| vc33 | L0@96 | yes |
| wa30 | L0@96 | yes |

Totals: 16/25 games reached level 1; 9/25 did not within 96 actions.

## Evidence classes

Scores are only comparable within an evidence class:

1. **Kaggle measured** -- an actual public leaderboard submission.
2. **Frozen paired causal** -- fresh matched arms, immutable protocol, exact
   replay, and causal attribution.  PCW v1.16 ar25 is here.
3. **Sealed evaluation** -- target frozen before observations and not modified
   after failures.
4. **Development** -- inspected public games, oracle-assisted work, or a solver
   changed after observing failures.  Useful for mechanism discovery only.
5. **Invalid** -- context overflow, transport failure, identity/replay failure,
   unequal starts, leakage, or support-authority violation.  Invalid is neither
   zero nor a negative model result.

## Update rules

When adding a result:

- link the durable artifact or submission ID;
- record protocol/commit, game and environment version, seed, level count,
  action count, replay status, and evidence class;
- keep untested (`-`), valid zero (`L0@n`), abstention, failure, and invalid
  separate;
- never promote a development result to sealed/held-out after inspecting it;
- never transfer a leaderboard score between solver versions;
- report actual ARC game scores only when baseline actions and the official
  scorer output are available.  Level completion alone is not an ARC score.

## Durable sources

- Current winner: `experiments/parallel-cognitive-workspace-v1-16/artifacts/SUMMARY.json`
- Kaggle submissions: `experiments/broad-shared-policy-v0/STATUS.md`
- Development matrix: `experiments/autonomous-progress-synthesis-v0/artifacts/online-registry-development/*/RESULT.json`
- Sealed breadth negative: `experiments/autonomous-progress-sealed-batch-v3/artifacts/fresh-1/RESULT.json`
