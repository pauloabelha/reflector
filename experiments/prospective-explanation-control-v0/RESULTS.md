# Results: Prospective Explanation Control v0

## Verdict: `NEGATIVE`

The frozen treatment was evaluated without per-game tuning. Prediction accuracy is secondary; the verdict follows the preregistered action/outcome gate.

**Execution scope:** user-directed early stop after the negative gate was reached. The full 40-packet cap was not completed; all results below come from durable chronological prefixes.

Observed packets: `ar25` 22, `cd82` 19, `sb26` 26, `sp80` 28, `cn04` 26, `g50t` 22, `ka59` 24.

## Cohort and configuration

Selection followed the exact mechanical procedure in `PROPOSAL.md`. Selected games: `ar25`, `cd82`, `sb26`, `sp80`, `cn04`, `g50t`, `ka59`.

Exact configuration: `{"beam_size": 8, "max_consequences_per_explanation": 16, "max_executed_overrides_per_game": 8, "max_expansions_per_decision": 128, "max_packets_per_game": 40, "seed": 0}`.

## Aggregate

- Games containing executed overrides: 3
- Improve / tie / worsen: 0 / 15 / 1
- Completed-level delta: -1
- Action-changing precision: 0.0
- False-override rate: 0.0625
- Prospective fallback: 95 (0.59375)
- Consequence prediction accuracy (secondary): 1.0
- Fallback/abstention reasons: `{"action-data-required": 17, "equivalent-futures": 1, "insufficient-supported-actions": 64, "no-active-consequence-match": 23, "no-prospective-evidence": 7}`
- Robustness / discrimination totals: 0 / 5
- Consequence expansions: 1846
- Score delta: unavailable

## Per game

| Game | Decisions | Overrides | Executed | Improve | Tie | Worsen | Level delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ar25` | 21 | 5 | 5 | 0 | 5 | 0 | +0 |
| `cd82` | 18 | 7 | 7 | 0 | 6 | 1 | -1 |
| `sb26` | 25 | 17 | 0 | 0 | 0 | 0 | +0 |
| `sp80` | 27 | 0 | 0 | 0 | 0 | 0 | +0 |
| `cn04` | 25 | 4 | 4 | 0 | 4 | 0 | +0 |
| `g50t` | 21 | 0 | 0 | 0 | 0 | 0 | +0 |
| `ka59` | 23 | 0 | 0 | 0 | 0 | 0 | +0 |

## Safeguards

- Both arms were ranked before the held-out packet was observed.
- Counterfactual successors were processed only by deep-copied runtimes.
- Every matched branch verified its predecessor frame hash.
- Actions requiring coordinate payloads abstained.
- Expansion, consequence, explanation, and override caps were enforced and traced.
- Game identity appeared only in transport/provenance, never in scoring.
- Serial/parallel structural verification: True.
- Repeated serial structural verification: True.
- Runtime wall/CPU totals: unavailable across the interrupted/resumed early-stop run.

## Every executed override

- `ar25:17`: arc-action:3 → arc-action:2; tie; level delta +0.
- `ar25:18`: arc-action:3 → arc-action:2; tie; level delta +0.
- `ar25:19`: arc-action:3 → arc-action:2; tie; level delta +0.
- `ar25:20`: arc-action:3 → arc-action:2; tie; level delta +0.
- `ar25:21`: arc-action:3 → arc-action:2; tie; level delta +0.
- `cd82:12`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cd82:13`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cd82:14`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cd82:15`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cd82:16`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cd82:17`: arc-action:5 → arc-action:2; worsen; level delta -1.
- `cd82:18`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cn04:22`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cn04:23`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cn04:24`: arc-action:5 → arc-action:2; tie; level delta +0.
- `cn04:25`: arc-action:5 → arc-action:2; tie; level delta +0.

## Negative cases and interpretation

All worsened cases: `[{"game": "cd82", "packet": 17}]`.

The smallest representational gap, if overrides remain rare, is the lack of grounded successor values: v0 can close only over exact structural effect signatures, not a fabricated future raster or semantic goal state.

No code was promoted into core.

Recurrent consequence schema hashes are recorded in `artifacts/summary.json`; full causal records for all overrides are in `artifacts/overrides.json`.
