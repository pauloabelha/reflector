# Qwen-to-R2 Generic Explanation Priors v0 — Results

Verdict: **ANCHOR_ONLY**.

| Game | Arm | Actions | Levels | Templates | Bound pairs | Confirmations | Prior decisions | Replay verified |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ar25 | human_reference | 17 | 1 | 1 | 1 | 13 | 14 | True |
| ar25 | qwen_mismatch | 32 | 0 | 4 | 1 | 5 | 31 | True |
| ar25 | qwen_own | 17 | 1 | 4 | 2 | 14 | 14 | True |
| ar25 | scratch | 32 | 0 | 0 | 0 | 0 | 0 | True |
| ar25 | self_built_reference | 17 | 1 | 1 | 1 | 13 | 14 | True |
| bp35 | qwen_mismatch | 32 | 0 | 4 | 0 | 0 | 0 | True |
| bp35 | qwen_own | 32 | 0 | 4 | 0 | 0 | 0 | True |
| bp35 | scratch | 32 | 0 | 0 | 0 | 0 | 0 | True |
| cd82 | qwen_mismatch | 32 | 0 | 2 | 0 | 0 | 0 | True |
| cd82 | qwen_own | 32 | 0 | 4 | 1 | 0 | 0 | True |
| cd82 | scratch | 32 | 0 | 0 | 0 | 0 | 0 | True |
| cn04 | qwen_mismatch | 32 | 0 | 4 | 0 | 0 | 0 | True |
| cn04 | qwen_own | 32 | 0 | 2 | 0 | 0 | 0 | True |
| cn04 | scratch | 32 | 0 | 0 | 0 | 0 | 0 | True |
| tr87 | qwen_mismatch | 32 | 0 | 4 | 0 | 0 | 0 | True |
| tr87 | qwen_own | 32 | 0 | 4 | 0 | 0 | 0 | True |
| tr87 | scratch | 32 | 0 | 0 | 0 | 0 | 0 | True |
| wa30 | qwen_mismatch | 32 | 0 | 4 | 1 | 0 | 0 | True |
| wa30 | qwen_own | 32 | 0 | 4 | 0 | 0 | 0 | True |
| wa30 | scratch | 32 | 0 | 0 | 0 | 0 | 0 | True |

## Primary comparisons

```json
[
  {
    "action_savings_fraction": null,
    "completion_gain": true,
    "completion_regression": false,
    "game": "ar25",
    "qualifying_improvement": true
  },
  {
    "action_savings_fraction": null,
    "completion_gain": false,
    "completion_regression": false,
    "game": "wa30",
    "qualifying_improvement": false
  },
  {
    "action_savings_fraction": null,
    "completion_gain": false,
    "completion_regression": false,
    "game": "cn04",
    "qualifying_improvement": false
  },
  {
    "action_savings_fraction": null,
    "completion_gain": false,
    "completion_regression": false,
    "game": "cd82",
    "qualifying_improvement": false
  },
  {
    "action_savings_fraction": null,
    "completion_gain": false,
    "completion_regression": false,
    "game": "tr87",
    "qualifying_improvement": false
  },
  {
    "action_savings_fraction": null,
    "completion_gain": false,
    "completion_regression": false,
    "game": "bp35",
    "qualifying_improvement": false
  }
]
```

Improved games: `['ar25']`.
Negative-control regression: `False`.
All final ledgers replay-verified: `True`.

Raw proposals, compiler decisions, action traces, and per-action checkpoints are under `artifacts/`.

## What happened on ar25

Qwen's first accepted hypothesis was the generic rule:

```text
SameInteriorLayout(?a, ?b)
→ Decrease(TranslationAlignmentResidual(?a, ?b))
```

On the live initial state, R2 uniquely grounded that effect to the solid candidate and solid target. It began with zero evidence, explored through the same deterministic fallback as scratch, then learned target-local opaque-action relative deltas. This hypothesis drove 13 actions. A second Qwen hypothesis—`AlignedHorizontal → Increase(residual)`—drove one action, but the complete action stream remained identical to both references: action 1 once, action 2 eleven times, and action 3 five times.

Thus Qwen did not recreate the richer triadic human/self-built explanation. It proposed a smaller sufficient pair prior, while R2 supplied grounding, consequence testing, and control. The mismatched wa30 proposal also uniquely grounded on ar25 and drove 31 actions but failed, demonstrating that grounding and local confirmation alone do not guarantee the right preferred consequence.

## Cross-game interpretation

- `cd82` had one live own-proposal binding but no directly observed relative-motion consequence, so the prior made zero decisions.
- `wa30`, `cn04`, `tr87`, and `bp35` own proposals were ambiguous or unbound and reduced exactly to scratch behavior.
- The negative control did not regress.
- No game outside ar25 improved, so this is evidence that generic external explanations can accelerate a known anchor—not yet evidence for Kaggle-level cross-game breadth.
