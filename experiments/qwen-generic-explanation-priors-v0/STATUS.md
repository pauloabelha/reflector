# Qwen-to-R2 Generic Explanation Priors v0 — Live Status

Machine checkpoints are written atomically under `artifacts/checkpoints/` after every real action. This file records human-readable partial results throughout the experiment.

## 2026-08-08 — Start checkpoint

- Branch: `qwen-generic-explanation-priors-v0`, based on relational-transfer result commit `8f64083`.
- Qwen server: local Qwen3-VL-4B-Thinking Q4_K_M with matched vision projector, running on `127.0.0.1:8081` as PID `215391`.
- Server policy: leave running after the experiment; no stop command will be issued.
- Input modality for v0: R2 structured state only. Prior local evidence found structured state more reliable than image+symbolic fusion.
- Prompt: one frozen byte-identical game-blind instruction; only the appended anonymous state varies.
- Qwen boundary: proposes explanations once before play; never sees outcomes and never chooses actions.
- Controller boundary: R2 validates, grounds, locally calibrates opaque actions, and controls.
- Current phase: freezing prompt, output schema, compiler language, and mechanical six-game cohort before any Qwen request.

## Recovery policy

- Freeze every raw Qwen request and response before real play.
- Write a two-phase pending/committed checkpoint around every target action.
- Reconstruct crashed environments by replaying committed ledgers and verifying full observation digests.
- Keep per-arm progress under `artifacts/progress/` and append completed arms here.
## 2026-08-08 22:08 BRT — Qwen residency repaired and verified

- The original detached server PID had been reaped by the command environment after reporting healthy.
- Qwen is now held by supervised foreground session `42716` on `127.0.0.1:8081` and will be left running after the experiment.
- `/v1/models` reports `qwen3-vl-4b-thinking-q4_k_m`; `nvidia-smi` reports 5,020 MiB total GPU memory in use.
- The load log accounts for approximately 3.46 GiB of Qwen CUDA buffers (2,375.91 MiB model, 612 MiB KV, 150.88 MiB language compute, 322.49 MiB vision compute).
- WSL does not attribute CUDA memory to individual Linux PIDs in its process table, so endpoint health plus load logs and aggregate VRAM are the residency evidence.

## 2026-08-08 22:12 BRT — Pre-inference implementation checkpoint

- The generic compiler, unique-pair grounder, locally confirmed pair-potential controller, four-step occlusion projection, and crash-safe real-ARC runner are implemented.
- The largest structured request was reduced from 64 KB to 11.4 KB by retaining eight representative figures and serializing symmetric relations once; ar25's complete triad remains present and uniquely groundable.
- Parallel audits found and fixed a latent-reappearance evidence bug before play: visible evidence is now measured from the visible predecessor rather than the latent forecast.
- Focused generic-prompt/compiler/grounding/controller tests: 14 passed.
- Full repository suite: 77 passed.
- No Qwen proposal request and no live target action had been issued at this checkpoint.
