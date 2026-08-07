# Real ARC-AGI-3 game-level matrix

> Observed official local development-game outcomes; not synthetic data and not a source-to-target transfer claim.

## Coverage

- Games: 25
- Levels: 62/183
- Completed games: 5
- Official local score: 25.959943125184/100
- Reached levels: 81/183
- Mean completed-level baseline/action ratio: 1.7418

Each scorecard game/version was matched to the local ARC download manifest, API metadata, environment metadata, and executable environment source. Hashes are in `results.json`.

## Completion matrix

`1` means completed, `0` means not completed, and `-` means that game has no such level.

|game\level|1|2|3|4|5|6|7|8|9|10|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|ar25|1|1|0|0|0|0|0|0|-|-|
|bp35|0|0|0|0|0|0|0|0|0|-|
|cd82|1|1|1|1|1|1|-|-|-|-|
|cn04|1|0|0|0|0|0|-|-|-|-|
|dc22|0|0|0|0|0|0|-|-|-|-|
|ft09|1|1|1|1|1|1|-|-|-|-|
|g50t|1|0|0|0|0|0|0|-|-|-|
|ka59|0|0|0|0|0|0|0|-|-|-|
|lf52|1|0|0|0|0|0|0|0|0|0|
|lp85|1|1|1|1|1|1|1|1|-|-|
|ls20|1|1|1|1|0|0|0|-|-|-|
|m0r0|1|0|0|0|0|0|-|-|-|-|
|r11l|1|0|0|0|0|0|-|-|-|-|
|re86|1|1|1|1|1|1|1|0|-|-|
|s5i5|1|1|0|0|0|0|0|0|-|-|
|sb26|1|1|1|1|1|1|1|1|-|-|
|sc25|0|0|0|0|0|0|-|-|-|-|
|sk48|0|0|0|0|0|0|0|0|-|-|
|sp80|1|0|0|0|0|0|-|-|-|-|
|su15|0|0|0|0|0|0|0|0|0|-|
|tn36|1|0|0|0|0|0|0|-|-|-|
|tr87|1|1|1|1|1|1|-|-|-|-|
|tu93|1|1|1|1|1|0|0|0|0|-|
|vc33|1|0|0|0|0|0|0|-|-|-|
|wa30|0|0|0|0|0|0|0|0|0|-|

## Interpretation boundary

This experiment answers which real public-development levels the frozen candidate completed and at what observed cost. The existing directed transfer atlas answers a different mechanistic question inside a synthetic executable family. Real source-to-target transfer requires running controlled prior/reset conditions in the official environments; this matrix does not pretend that completion adjacency establishes that causal effect.
