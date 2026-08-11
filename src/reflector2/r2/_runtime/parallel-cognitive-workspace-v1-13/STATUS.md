# Parallel Cognitive Workspace v1.13 status

## 2026-08-09 — preregistration

- v1.12 is preserved as phase-dispatch INVALID.
- Frozen sole repair: distinguish pre-probe grounding revision from
  post-probe prospective-evidence revision in the strict response adapter.
- No v1.13 ARC environment has been opened and no v1.13 Qwen request made.

## 2026-08-09 — freeze ready

- A preserved real ambiguity-repair turn now builds the strict response schema
  without a causal packet, requires one relation-set address, forbids a
  premature prospective address, and uses the small revision-only prompt.
- A preserved post-probe packet still requires both relation and prospective
  addresses. Thus the two live phases are mechanically distinct and covered.
- v1.12/v1.13 and v1.9/v1.11 focused invocations pass (`31 passed` total), as
  do dry-run manifest construction and `git diff --check`.
- No semantic/controller/configuration change beyond phase dispatch was made.

## 2026-08-09 12:35:04 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
- COMPLETE `generic_prospective/ar25/shared_live_qwen`: levels=0, actions=64, Q→R grounded=1, replay=True.

## 2026-08-09 — final mechanistic result

- Verdict: **valid control-chain failure**. Both fresh arms reached the 64-action
  budget at level 0, began from the same state, and replayed exactly. The shared
  arm had four successful transports and four valid JSON compilations; maximum
  prompt occupancy was 13,430 / 24,576, with zero authority violations.
- The live initial Qwen schema was
  `DifferentArea(?a,?b) & DifferentOutline(?a,?b) ->
  Decrease(TranslationAlignmentResidual(?a,?b))`. R2 grounded it to three
  alternatives, recorded one grounded Qwen-to-R2 pickup, and spent the four
  ambiguity-probe slots. Eight selected prediction objects received
  environment-authored support.
- Qwen then reacted to the returned transition evidence by proposing
  `MovedWhileStationary(?a,?b) -> Decrease(TranslationAlignmentResidual(?a,?b))`
  on every repair turn. Each revision was conservatively rejected as
  `grounding-validation-unknown`; no revised schema became executable, no
  confirmation probe occurred, and `prior_decisions=0`.
- Root cause: the three original alternatives paired each 45-cell task figure
  with a 316-cell frame/HUD component. The returned ambiguity witness made
  `MovedWhileStationary` salient but did not expose a complete predicate-to-pair
  table. In the exact complete grounding, that predicate retains four unordered
  pairs and is not unique. `MovedTogether` selects a pair with invariant relative
  distance, whereas `SameInteriorLayout` uniquely selects the pair with observed
  relative-motion control leverage.
- Required successor change is generic: preserve the frame/HUD in the shared
  world but type it separately from control-eligible task entities, and return
  exact closed-world predicate extension plus probe-derived control-leverage
  diagnostics to Qwen. Do not inject a frozen schema or game-specific identity.
