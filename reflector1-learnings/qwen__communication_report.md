# Qwen multimodal-fusion goal report

## Outcome

The requested frozen local experiment was completed in full on 2026-08-05.
All **104/104** planned Qwen3-VL-4B-Thinking requests ran against the verified
cache-disabled localhost server, including two repeats of every arm and the four
corrupted-fusion controls. The server was stopped cleanly afterward. Reflector
and real game source code were not modified.

The result is negative for always-on fusion:

- image only (I): mean partial score **0.576**;
- ASCII only (A): **0.262**;
- structured state only (S): **0.600**;
- fused image + ASCII + state (F): **0.300**;
- paired `F-I`: **-0.277**;
- paired `F-S`: **-0.300**;
- paired `S-A`: **+0.339**.

Fusion did not meet the preregistered synergy criterion. It exceeded both I and
S on only one case (the symbolic marker), rather than on multiple distinct
transformation types.

## What the experiment says

Structured JSON was the strongest default representation. It preserved exact
coordinates, stable IDs, and object relations, and substantially outperformed
raw ASCII. Images remained valuable for direct visual attributes: they had the
best changed-object recall, transformation accuracy, and strict-output validity.

The tested fused payload did not successfully combine those strengths. Strict
JSON validity fell to **9/24** for F, versus **22/24** for I and **18/24** for S.
Many failures duplicated a plausible JSON object around `</think>` or appended
formatting text. Outputs were intentionally not repaired, so the correct claim
is that fused requests underperformed end to end—not that pixels inherently
damage causal reasoning.

Conflict handling was poor. All eight corrupted-fusion outputs were strict
invalid, and none correctly identified its controlled corruption. In raw content,
Qwen followed corrupted symbolic color, identity, and coordinate values without
reporting conflict. On the missing-object case it emitted a conflict-like message
but invented an incorrect merged-object explanation. This indicates symbolic
over-trust rather than robust cross-modal checking.

## Recommendation

Use **structured state only** for the first Reflector splice. Keep raw frames for
an optional second pass when the state parser cannot represent color nuance,
shape, occlusion, or visible markers. Do not send both modalities in every
strict-JSON request until a new preregistered test demonstrates reliable output
serialization and correct disagreement detection.

## Reproducibility and deliverables

The main experiment directory is:

`/home/pauloabelha/alienware16-llm/qwen/experiments/multimodal_fusion/`

It contains:

- `preregistration.md` — frozen design and scoring rules;
- `experiment.py` — standard-library generator, runner, scorer, and report code;
- `fixtures/` — 12 PNG pairs, ASCII, structured states, corruptions, ground truth,
  and the saved randomized arm manifest;
- `artifacts/` — all requests, raw responses, direct parses, timing, GPU samples,
  and per-run scores;
- `results.json` — complete machine-readable results;
- `per_case_scores.csv` — per-run score table;
- `aggregate_paired_comparisons.csv` — requested paired comparison table;
- `report.md` — full scientific report and limitations.

There were no retained-run transport failures. Verbatim model content matched
between repeats for **50/52 (96.2%)** case-arm pairs. Peak total sampled VRAM was
about 5032 MiB across arms, with no OOM or server instability.
