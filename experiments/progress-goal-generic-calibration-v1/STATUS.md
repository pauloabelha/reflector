# Goal-agnostic calibration status

- Pure stable correspondence tracker implemented after the frozen g50t harness
  failure.
- It observes every region under every opaque intervention before any goal
  family is proposed, preserving competing controlled candidates and all
  appearance/disappearance/motion effects.
- The inherited live runner now exposes a tracker hook. The goal-agnostic path
  renders stable tracked IDs, every per-entity effect, the unique controlled
  candidate when one exists, learned displacement models, and unexplained
  interventions before Qwen sees any goal family.
- A fresh wa30 regression is frozen as v6 before another cross-game selection.
