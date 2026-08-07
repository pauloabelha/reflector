# Compact causal comparison table

## Within-game persistence

| Game | L reached / score / actions | G reached / score / actions | A reached / score / actions | G-L (levels, score, actions) | Verdict |
|---|---:|---:|---:|---:|---|
| lp85 | 1/8 / 0.586397 / 400 | 8/8 / 72.958482 / 351 | 8/8 / 72.958482 / 351 | +7, +72.372084, -49 | useful within-game cumulative learning |
| ls20 | 3/7 / 14.963681 / 400 | 4/7 / 30.341314 / 400 | 4/7 / 30.341314 / 400 | +1, +15.377633, +0 | useful within-game cumulative learning |
| tu93 | 1/9 / 1.657484 / 400 | 5/9 / 33.333333 / 400 | 5/9 / 33.333333 / 400 | +4, +31.675849, +0 | useful within-game cumulative learning |
| sc25 | 0/6 / 0.000000 / 400 | 0/6 / 0.000000 / 400 | 0/6 / 0.000000 / 400 | +0, +0.000000, +0 | no observable opportunity/effect of between-level persistence |

## Cross-game transfer

| Direction | P reached / score / actions | R reached / score / actions | First P-R trajectory index (zero-based) | Outcome delta P-R | Verdict |
|---|---:|---:|---:|---:|---|
| lp85 → ls20 | 4/7 / 30.341314 / 400 | 4/7 / 30.341314 / 400 | none | +0, +0.000000, +0 | inert internal persistence (no action or outcome effect) |
| lp85 → sc25 | 0/6 / 0.000000 / 400 | 0/6 / 0.000000 / 400 | none | +0, +0.000000, +0 | inert internal persistence (no action or outcome effect) |
| ls20 → tu93 | 5/9 / 33.333333 / 400 | 5/9 / 33.333333 / 400 | none | +0, +0.000000, +0 | inert internal persistence (no action or outcome effect) |
| tu93 → ls20 | 4/7 / 30.341314 / 400 | 4/7 / 30.341314 / 400 | 288 | +0, +0.000000, +0 | inert behavioral persistence (action divergence, no outcome effect) |
| sc25 → lp85 | 8/8 / 72.958482 / 351 | 8/8 / 72.958482 / 351 | none | +0, +0.000000, +0 | inert internal persistence (no action or outcome effect) |
