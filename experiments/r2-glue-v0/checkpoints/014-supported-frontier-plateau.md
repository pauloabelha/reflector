# Checkpoint 014: supported-goal frontier plateaus

Time: 2026-08-12

## Failure

AR25 had accumulated real support for its occupancy-versus-negative-space
potential, but later oscillated between residuals 27 and 30. Lifetime support
therefore correctly protected the goal from failure repair, while a naive
consecutive-nonprogress counter was reset by each 30 → 27 recovery. Returning
to an old best was mistaken for renewed control progress even though the
frontier did not advance.

## Repair

- Each semantic goal tracks its best observed potential and the measured steps
  since that frontier last improved.
- Four steps without a new best request a focused complementary semantic
  hypothesis only when the goal already has environment-confirmed progress.
- A supported plateau does not suspend or retire the proven goal, its role
  trajectories, or independently learned mechanisms.
- The compiler preserves the canonical prior goal and admits only valid,
  semantically distinct refinements; model abstention cannot erase the goal.
- An accepted repair acknowledges exactly one `(semantic goal, best frontier)`
  epoch. Rejected repair remains pending; a newly improved frontier permits a
  later independent plateau repair.
- No game, palette, coordinate, entity, action, verb meaning, or solution is
  encoded.

## Evidence

- Unit replay of a potential worsening and recovery to the old best preserved
  two frontier-stagnation steps despite positive local progress on the return.
- Exact fresh AR25 reached best residual 27 with seven progress confirmations,
  then accumulated four no-new-best steps across the 27/30 oscillation.
- The return 30 → 27 was locally positive and produced an eighth confirmation,
  but correctly advanced frontier stagnation to four rather than resetting it.
- The supported goal retained the same semantic key and remained control
  eligible while the focused repair ran.
- Qwen acknowledged the plateau and abstained from a second structured goal;
  the compiler retained the original goal and all evidence.
- Ledger request at source action 17 contained
  `supported-goal-plateau` and `r2-goal-potential-plateau`; the immediately
  following source-action-18 request contained neither, proving accepted repair
  was one-shot for that frontier.
- 111 focused tests pass. The full suite has 254 passes and one unchanged
  missing historical artifact failure.

This establishes a generic distinction between goal validity and controller
stagnation. It does not establish an AR25 terminal, level completion, score
improvement, or cross-game competence.
