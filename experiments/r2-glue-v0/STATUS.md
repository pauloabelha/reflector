# R2 glue status

## Current state

- Phase: semantic contract/feedback liveness verified; cross-game audit next.
- Branch: `glue` at baseline `75600da`.
- Production baseline: pushed to `origin/main`.
- Focused baseline verification: 123 tests passed.
- Live starting case: AR25, with no claim of transfer or score improvement.

## Checkpoints

| ID | State | Result |
|---|---|---|
| 000 | complete | Main architecture promoted; live semantic-to-control seam isolated |
| 001 | complete | Generic semantic measurement proposal and compiler; 135 focused tests pass |
| 002 | complete | Malformed goals quarantined; CAE feedback retained; stale failed goals retired |
| 003 | pending | Cross-case/non-overfit audit |

## Current hypothesis

R2 is not mainly missing another planner. It is losing useful semantic
abductions at the boundary between Qwen prose and R2-measurable schemas. The
closed prompt/schema supplies a meaning for FIT before observation, while the
abduction channel can only compose existing stable schema IDs. Opening that
boundary safely may let Qwen propose why a goal matters while preserving R2's
grounding and settlement authority.

## Next evidence

1. Run at least one additional game/capability case selected independently of
   whether it favors spatial-set measurements.
2. Reject the intervention if it merely improves language while leaving control
   unchanged.
