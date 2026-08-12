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

## Verification so far

- 43 targeted semantic, planner, and Qwen tests pass.
- The full suite has 239 passes and one unchanged missing historical artifact.
- Fresh BP35 play grounded a normalized-boundary alignment proposal as
  `PROBE_ELIGIBLE`; an identity-broken settlement did not increment
  nonprogress, as required.

The live threshold/revision sequence and the predeclared CD82 transfer run
remain open. No performance or completion claim is made.
