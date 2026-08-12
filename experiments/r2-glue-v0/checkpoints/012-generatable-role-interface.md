# Checkpoint 012: generatable role interface and AR25 local progress

Time: 2026-08-12

## Failure

Across recorded runs from five games, 51 goal proposals failed dependent role
typing: 44 used invalid constraint arguments and 7 repeated formal roles.
Separately, AR25's useful hole residual was hard-gated by Qwen's unsupported
`required same_outline` guess.

## Repair

- New measurable goal generation uses canonical binary ports `actor,target`.
- Potential ports and constraint arguments share those exact formal ports.
- The legacy compiler continues to read prior multi-role proposals.
- Newly generated visual categorical clues are defeasible: suggested,
  anti-clue, or unknown; they cannot become hard requirements.
- Verbs, games, palettes, action meanings, coordinates, and solutions are not
  mapped or encoded.

## Evidence

- Fresh CD82 compiled two consecutive canonical-port goals with no rejection.
- After grounded nonprogress, Qwen validly abstained and R2 dropped the goal.
- Fresh AR25 grounded occupancy against enclosed negative space even though
  the suggested same-outline clue was false.
- The AR25 residual decreased 53 → 32 with six progress confirmations.
- Control advanced from probe eligibility to causal-factorized plan eligibility.
- 147 focused tests pass.
- The full suite has 251 passes and one unchanged missing historical artifact
  failure.

This establishes semantic pickup and local measured progress. It does not yet
establish an environment level or score terminal.
