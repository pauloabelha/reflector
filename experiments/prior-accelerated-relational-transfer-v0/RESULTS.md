# Prior-Accelerated Relational Transfer v0 — Results

Verdict: **INCONCLUSIVE**.

Mechanically selected positive target: `wa30` at source-distance `[1, 1, 0, 1]`.
Mechanically selected negative control: `cn04`.
Action budget per arm: 32.

| Role | Game | Arm | Actions | Levels | Prior decisions | Local confirmations | Abstentions | Replay verified |
|---|---|---|---:|---:|---:|---:|---:|---|
| negative | cn04 | combined | 32 | 0 | 0 | 0 | 32 | True |
| negative | cn04 | external | 32 | 0 | 0 | 0 | 32 | True |
| negative | cn04 | scratch | 32 | 0 | 0 | 0 | 32 | True |
| negative | cn04 | self_transfer | 32 | 0 | 0 | 0 | 32 | True |
| positive | wa30 | combined | 32 | 0 | 0 | 0 | 32 | True |
| positive | wa30 | external | 32 | 0 | 0 | 0 | 32 | True |
| positive | wa30 | scratch | 32 | 0 | 0 | 0 | 32 | True |
| positive | wa30 | self_transfer | 32 | 0 | 0 | 0 | 32 | True |

## Transfer comparisons

```json
[
  {
    "action_savings": null,
    "action_savings_fraction": null,
    "arm": "self_transfer",
    "completion_gain": false
  },
  {
    "action_savings": null,
    "action_savings_fraction": null,
    "arm": "external",
    "completion_gain": false
  },
  {
    "action_savings": null,
    "action_savings_fraction": null,
    "arm": "combined",
    "completion_gain": false
  }
]
```

Negative-control regression: `False`.
All final ledgers replay-verified: `True`.

See `selected_targets.json`, `self_built_schema.json`, per-action JSONL traces, and atomic checkpoints for the full audit trail.

## Secondary fresh-ar25 sanity check

This was executed only after the primary target/control verdict was fixed. It
tests whether the proposed schema/prior interface can control a fresh instance
of its source game without transferring source action IDs.

| Arm | Actions | Level 1 | Prior decisions | Overrides | Replay verified |
|---|---:|---|---:|---:|---|
| scratch | 32 | no | 0 | 0 | true |
| self-transfer | 17 | yes | 14 | 14 | true |
| external | 17 | yes | 14 | 14 | true |
| combined | 17 | yes | 14 | 14 | true |

The successful arms learned target-local opaque action consequences and then
reduced the alignment residual to zero. Their action counts were `1 + 11 + 5`;
the identical sequence follows from local geometry and calibration, not a
transferred source action token.

This is positive evidence for the **input boundary**: R2 can receive or
transfer an action-agnostic relational control schema and use it to solve real
ar25 level 1. It is not yet positive cross-game transfer evidence. On `wa30`,
the nearest static motif bound to the wrong causal carrier, so the prior never
obtained a target-local consequence and correctly abstained.
