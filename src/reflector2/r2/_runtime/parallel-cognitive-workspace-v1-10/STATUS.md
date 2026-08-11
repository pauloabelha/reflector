# Parallel Cognitive Workspace v1.10 status

## 2026-08-09 — replacement preflight

- v1.9 was preserved as implementation `INVALID`; its artifacts are excluded.
- This version changes only the graph criticism vocabulary and experiment
  identity/artifact root.
- No v1.10 environment has been opened and no v1.10 Qwen request has been made.
- Pending before launch: real-reducer replay test, full v1.9 regression suite,
  dry-run manifest, resident-server verification, and a git checkpoint.

## 2026-08-09 — implementation freeze ready

- The authoritative v1.4 graph reducer now admits exactly the new
  `prospective-evidence-return` status; no other reducer or control semantics
  changed.
- A real-reducer regression proves ingestion at support zero, target/evidence
  dependency preservation, and canonical event replay.
- The complete v1.9 + v1.10 suite passes (`17 passed`), as do module compilation,
  wrapper dry-run/manifest construction, and `git diff --check`.
- Configuration remains unchanged except experiment/protocol identity. The
  resident Qwen server/model/context were already verified immediately before
  the v1.9 run and remain resident; they will be checked once more before reset.
- Live scientific and causal gates remain entirely untested in v1.10. The next
  action is one new fresh paired run; no v1.9 artifact is eligible for loading.

## 2026-08-09 — fresh paired result

- Frozen checkpoint: git commit `69c21d4`.
- Binary verdict: **valid FAIL**.
- Both arms started from digest
  `8c9c38b5c049817e37ea6525b513983e3628a3f1224df5eafb3146175bb2a51b`,
  used 64 actions, completed zero levels, ended at digest
  `d575fa2426d4d502aac4bcd4529edb3c29687fc61f5616605292bb4b9431971d`,
  and replayed exactly. Their factual action sequences were identical.
- Shared cognition completed all four required Qwen calls with four valid JSON
  compilations, zero transport errors, zero support-authority violations, and
  valid context admission. Maximum prompt use was 13,360 of 24,576 tokens;
  prompt plus the 2,048 reserve fit comfortably.
- Qwen's sole semantic schema was
  `AlignedHorizontal(?a,?b) AND DifferentArea(?a,?b) -> Decrease
  TranslationAlignmentResidual(?a,?b)`. R2 found zero groundings and persisted
  an exact `unbound` criticism.
- The later three responses did not repair it: one attempted schema write was
  rejected for a duplicate evidence ID, and the final two were rejected as
  alpha-equivalent repeats. Situated explanations were false/rejected.
- Consequently there were zero live bindings, grounded pickups, selected
  probes, supported objects, prior decisions, changed actions, or
  counterfactual branches. The new prospective evidence-return mechanism was
  available but could not activate because no schema grounded.
- Scientific conclusion: transport, shared residency, criticism return,
  context, authority, and replay are working. The current unbound criticism is
  too weak for this 4B model: an empty candidate set says the conjunction fails
  but does not identify which clause eliminated viable assignments or expose
  condition-wise near misses. Any next experiment requires a new version and
  must improve that generic diagnostic rather than inject an ar25 schema.

## 2026-08-09 11:39:35 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
- COMPLETE `generic_prospective/ar25/shared_live_qwen`: levels=0, actions=64, Q→R grounded=0, replay=True.
