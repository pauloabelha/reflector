# R2 glue status

## Current state

- Phase: cross-game safety transfer verified; control-efficiency audit active.
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
| 003 | complete | bp35 selected independently; semantic probe grounded and settled without false authority |
| 004 | active | Mechanism/goal evidence split implemented; BP35/CD82 live transfer audit continues |

## Current hypothesis

R2 is not mainly missing another planner. It is losing useful semantic
abductions at the boundary between Qwen prose and R2-measurable schemas. The
closed prompt/schema supplies a meaning for FIT before observation, while the
abduction channel can only compose existing stable schema IDs. Opening that
boundary safely may let Qwen propose why a goal matters while preserving R2's
grounding and settlement authority.

## Next evidence

1. Complete the repeated uniquely grounded BP35 nonprogress sequence and verify
   that the semantic proposal is revised while its learned effect remains.
2. Run `cd82`, predeclared as the next lexical game, without an intervening code
   change; treat it as a falsification test, not a tuning case.
3. Determine whether equivalent-role ambiguity can be quotiented by generic
   symmetry and intervention evidence without losing causal alternatives.
