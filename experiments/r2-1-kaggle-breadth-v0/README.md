# R2.1 Kaggle breadth experiment v0

This experiment runs the controller documented in `R2_1.md` across every
locally installed ARC-AGI-3 game while preserving its epistemic authority
boundaries. It measures actual level completion, actions, replay integrity,
Qwen participation, failures, and timeouts. Recursive depth or binding volume
is diagnostic evidence only.

The schedule interleaves keyboard, click, mixed-control, and uncategorized
games so a deadline-truncated run remains mechanic-diverse. Each episode uses a
fresh interpreter and artifact directory. Within an episode, R2.1 retains
supported mechanics across level transitions and re-grounds situated bindings.

The preregistered first pass starts all 25 games at level 1. Only spare time is
used for later start-level passes. The parent keeps a finalization reserve and
atomically updates `summary.json` after every episode.

This is an adaptive development campaign, not a sealed transfer claim. Small
mechanism changes may be made after inspecting completed traces. Every complete
episode records the exact R2.1 experiment and configuration hashes so results
from different builds remain separable. Any promoted change still requires a
paired causal check and a later frozen mechanic-diverse evaluation.

Run from the repository root:

```bash
.venv/bin/python experiments/r2-1-kaggle-breadth-v0/run.py
```
