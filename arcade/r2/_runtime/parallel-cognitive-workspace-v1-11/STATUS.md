# Parallel Cognitive Workspace v1.11 status

## 2026-08-09 — preregistration

- v1.10 is preserved as a valid no-binding FAIL; none of its cognition or
  artifacts may seed this run.
- Frozen change: generic condition-wise unbound diagnostics, unique evidence
  citations, and four event-aligned call sources `0,8,16,24`.
- No v1.11 environment has been opened and no v1.11 Qwen request has been made.

## 2026-08-09 — implementation freeze ready

- The near-miss regression recreates the v1.10 failure shape and proves the
  witness identifies both mutually incompatible clauses, including the viable
  effect pair recovered by leaving each clause out.
- The event-aligned call schedule and unique evidence grammar are regression
  checked. The focused cognition/evidence suites pass (`17 passed` total), as
  do compilation, dry-run manifest construction, and `git diff --check`.
- No action meaning, game note, historical schema, recorded outcome, or prior
  cognitive artifact was added. The resident Qwen server remains loaded.

## 2026-08-09 — fresh paired result

- Frozen checkpoint: git commit `81027db`.
- Binary verdict: **INVALID (mandatory-context feasibility)**. This is not a
  valid scientific FAIL.
- Control used 64 actions, remained at level 0, and replayed exactly. Shared
  stopped safely at action 16 before constructing an incomplete Qwen request.
- The run nevertheless crossed a new mechanistic boundary before invalidation:
  Qwen's live initial schema grounded to three competing bindings; R2 exposed
  one grounded Qwen-to-R2 pickup, used the four ambiguity-probe slots, and the
  environment created eight support edges for selected predictions. No support
  authority violation occurred.
- The immediate repair request at source 8 contained the exact ambiguity
  witness. Qwen's reasoning inspected the candidate relation table, but its
  2,048-token completion ended at the limit before finishing JSON; the required
  call therefore had a transport/compile failure.
- At action 16 the exact causal closure for the next repair turn cost 17,873
  frontier units versus the frozen 6,400 budget. The runner correctly raised
  `FrontierBudgetError` rather than silently dropping evidence.
- Root cause is representational redundancy, not missing world evidence: four
  cumulative prospective-return criticisms each repeat grounding/evidence
  payloads, while their exact dependency closure also carries the underlying
  evidence, predictions, bindings, frames, and relation packet. The next
  version must render one losslessly packed causal packet and avoid recursive
  retransmission; merely raising the budget would likely exceed the 24,576
  model context. A larger completion reserve or smaller revision-only response
  grammar is also required because the repair answer hit the 2,048-token cap.

## 2026-08-09 11:58:45 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- FAILED `generic_prospective/ar25/shared_live_qwen`: FrontierBudgetError: frontier budget 6400 is below mandatory closure cost 17873.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
