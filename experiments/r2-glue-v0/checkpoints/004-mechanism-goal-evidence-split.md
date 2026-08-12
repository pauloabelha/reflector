# Checkpoint 004: mechanism and goal evidence split

Time: 2026-08-12

## Generic failure

BP35 showed that R2 could learn an action-conditioned stationary effect and
measure zero progress while Qwen continued to supply the same plausible goal.
The architecture counted a correct mechanism prediction as confirmation of the
whole explanation. It also projected the pre-action candidate after settlement,
delaying fresh judgments by one decision.

## Repair

R2 now maintains positive `progress_confirmations` separately from mechanism
`confirmations`. A uniquely grounded non-positive measurement increments a
nonprogress counter. At two observations, with no positive progress support and
no supported competitor, the semantic scheduler requests a revised proposal.
The mechanism model is explicitly preserved. Settlement projection reads the
observer's current counters, so the semantic abductor receives the evidence at
the boundary that generated it.

The repair uses no game ID, action ID, coordinate, color, shape, verb mapping,
or solution rule. The threshold and supported-competitor guard apply to every
measurable goal proposal.

## Verification

- 43 targeted semantic, planner, and Qwen tests pass.
- The full suite has 239 passes and one unchanged missing historical artifact.
- Fresh BP35 play grounded a normalized-boundary alignment proposal as
  `PROBE_ELIGIBLE`; an identity-broken settlement did not increment
  nonprogress, as required.
- With no intervening code change, CD82 grounded a boundary residual as
  `PROBE_ELIGIBLE`. The same candidate exposed zero-progress counts 1, 2, and 3
  immediately after settlement. Semantic revision first retained a structurally
  distinct interior-compatible alternative, then retired the goal list to
  empty by turn 7 after the alternative failed to acquire support.

The live trace verifies the feedback and revision boundary, not performance:
CD82 was not completed and no score or useful-control claim is made.
