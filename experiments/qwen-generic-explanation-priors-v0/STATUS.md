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
- Qwen partial 1/6: `ar25` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 2/6: `wa30` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 1/6: `ar25` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 2/6: `wa30` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 3/6: `cn04` transport_error=None, valid_contract=True, accepted=2, rejected=0.
- Qwen partial 3/6: `cn04` transport_error=None, valid_contract=True, accepted=3, rejected=0.

## 2026-08-08 22:16 BRT — Proposal run invalidated before play

- The first orchestration client remained alive after its tool session appeared to end. A second client was started, causing two preparation processes to race.
- ar25 and wa30 produced duplicated status entries from reuse of the same completed files. cn04 received two actual completions, observed as accepted-count 2 and 3; the shared atomic path retained only the last writer.
- Both preparation clients were stopped before any ARC environment action. The Qwen server itself remained loaded and healthy.
- This proposal run is scientifically invalid and will not be used. Its files are preserved under `artifacts-contaminated-duplicate-prepare-20260808T2216/` rather than deleted.
- The clean rerun uses seed 1730, an empty artifact namespace, and an OS-level exclusive preparation lock, so a second client fails before sending a request.
- Qwen partial 4/6: `cd82` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 1/6: `ar25` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 2/6: `wa30` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 3/6: `cn04` transport_error=None, valid_contract=True, accepted=2, rejected=0.
- Qwen partial 4/6: `cd82` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 5/6: `tr87` transport_error=None, valid_contract=True, accepted=4, rejected=0.
- Qwen partial 6/6: `bp35` transport_error=None, valid_contract=True, accepted=4, rejected=0.

## Frozen pre-play manifest

- All six raw requests, raw responses, compiler decisions, and structured inputs are durable.
- `FROZEN_MANIFEST.json` was written before any live target action.
- The instruction hash is identical across games; only each anonymous structured state differs.

## 2026-08-08 22:21 BRT — Frozen proposal preflight

- Clean accepted hypotheses: ar25=4, wa30=4, cn04=2, cd82=4, tr87=4, bp35=4; every response satisfied the strict JSON contract with zero compiler rejections.
- Unique own-proposal effect pairs on the frozen initial snapshots: ar25=2 and cd82=2.
- All own proposals for wa30, cn04, tr87, and bp35 are ambiguous or unbound and therefore must abstain unless the live initial snapshot changes grounding.
- No real ARC action had been executed. The next phase is 20 isolated, checkpointed first-level arms.
- The `cd82` line appearing immediately after the invalidation heading was a late status append from the quarantined in-flight request; it is not part of the clean artifact namespace or manifest.

## Live real-ARC run started

- 20 isolated arms launched with up to 4 workers.
- Every action uses pending→committed atomic checkpoints; each final ledger gets a fresh replay.
- Arm partial `ar25/human_reference`: actions=17, levels=1, bound=1, confirmations=13, prior_decisions=14, replay=True.
- Arm partial `ar25/qwen_own`: actions=17, levels=1, bound=2, confirmations=14, prior_decisions=14, replay=True.
- Arm partial `ar25/self_built_reference`: actions=17, levels=1, bound=1, confirmations=13, prior_decisions=14, replay=True.
- Arm partial `ar25/scratch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `ar25/qwen_mismatch`: actions=32, levels=0, bound=1, confirmations=5, prior_decisions=31, replay=True.
- Arm partial `wa30/scratch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `wa30/qwen_own`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `wa30/qwen_mismatch`: actions=32, levels=0, bound=1, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `cn04/scratch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `cn04/qwen_own`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `cn04/qwen_mismatch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `cd82/scratch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `cd82/qwen_own`: actions=32, levels=0, bound=1, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `cd82/qwen_mismatch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `tr87/scratch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `tr87/qwen_own`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `tr87/qwen_mismatch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `bp35/scratch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `bp35/qwen_own`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.
- Arm partial `bp35/qwen_mismatch`: actions=32, levels=0, bound=0, confirmations=0, prior_decisions=0, replay=True.

## Live run complete

- Verdict: `ANCHOR_ONLY`.
- Improved games: `['ar25']`.
- All final ledgers replay-verified: `True`.

## 2026-08-08 22:23 BRT — Causal wrap-up

- ar25 Qwen-own solved in 17 actions versus scratch failing at 32, exactly matching human-reference and transferred-self-built-reference action counts and action sequence.
- The main Qwen driver was `SameInteriorLayout(?a,?b) → Decrease(TranslationAlignmentResidual(?a,?b))`, uniquely grounded to the candidate/target pair; it drove 13 actions after local confirmation.
- Qwen's secondary aligned-pair/increase hypothesis drove one action but did not change the successful sequence relative to the references.
- A mismatched wa30 prior uniquely grounded on ar25, drove 31 actions, and failed—an important causal negative rather than a cosmetic comparison.
- cd82's own prior bound one pair but received zero direct relative-motion confirmations and therefore made zero decisions. Other non-anchor own priors abstained through ambiguity or lack of binding.
- The honest conclusion is `ANCHOR_ONLY`: the generic external explanation interface can solve ar25.1 faster, but this vocabulary/prompt/controller combination did not transfer a win to another first level.
