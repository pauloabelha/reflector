# Parallel Cognitive Workspace v1.9 status

## 2026-08-09 — preregistration preflight

- Preregistration and frozen intended config written only.
- At the instant this preregistration was written, no v1.9 code or tests
  existed. Implementation and test files were added concurrently afterward by
  separate tasks; they are not reviewed or certified by this preregistration
  checkpoint and must be reconciled against the frozen proposal before launch.
- No environment has been opened and no Qwen request has been made.
- Fresh live artifacts do not exist.
- Frozen intended pair: `ar25`, `r2_only` versus `shared_live_qwen`, one
  independent fresh environment per arm, at most two ARC workers.
- Frozen action budget: 64 per arm; level target: 1.
- Frozen Qwen boundaries: sources `0, 12, 24, 36`, integrated eight logical
  actions later; maximum four calls.
- Frozen Qwen capacity: context 24,576; completion reserve and maximum 2,048;
  thinking budget 1,024.
- Frozen probe partition: at most four ambiguous-population probes plus one
  reserved unique-revision confirmation probe; total at most five.
- Required new mechanism: exact prospective evidence-return
  criticism/revision packet for every qualifying live evidence return,
  including a uniquely grounded supported proposal.
- Original strict causal `PASS` / valid `FAIL` / hard `INVALID` distinction is
  retained.

Before launch, implementation and regression tests must prove packet causal
ancestry and graph-coverage equality, no future evidence, the typed probe
partition, context capacity including reserve, strict compilation, support
authority, checkpoint recovery, isolation, and exact factual/counterfactual
replay. The effective config, code hashes, model hash, server `n_ctx=24576`, and
manifest must then be frozen before either arm resets.

## 2026-08-09 — implementation reconciliation

- The concurrently added implementation was reconciled against the frozen
  proposal without opening an ARC environment or sending a Qwen request.
- The live controller enforces the typed `4 + 1` probe partition and rebuilds
  its counters from durable plans.
- The evidence bridge grants support/refutation only to predictions selected
  by an actual probe/control plan; unselected fallback predictions remain
  calibration observations.
- A selected prospective judgment now creates an exact, dependency-linked
  `prospective-evidence-return` criticism. Its grounding packet is explicitly
  action-free, versioned, and refuses to claim completeness when the bounded
  entity extractor is saturated.
- The cognition adapter exposes the causally prior environment evidence to the
  next revision turn and accepts a revision only when complete grounding leaves
  one effect pair.
- Focused v1.9 tests, module compilation, the inherited CLI import, dry-run
  manifest construction, and `git diff --check` pass. Live transport, replay,
  causal completion, and the binary gate remain untested until the fresh pair.
- The resident server was verified awake before freeze: alias
  `qwen3-vl-4b-thinking-q4_k_m`, llama.cpp build `b8660-d00685831`, one slot,
  vision enabled, `n_ctx=24576`. The model SHA-256 is
  `474ecaf1284aa6ff3273fb796c3cba55d2ee33ec0d8c63464fbd84500a9a462d`.

## 2026-08-09 — fresh paired run result

- Frozen checkpoint: git commit `72bc3e8`.
- Binary verdict: **INVALID (implementation protocol mismatch)**. This is not a
  valid scientific failure and no PASS/FAIL inference is made.
- `r2_only` completed its 64-action budget at level 0 and exact replay passed;
  final digest
  `d575fa2426d4d502aac4bcd4529edb3c29687fc61f5616605292bb4b9431971d`.
- `shared_live_qwen` durably reached action 8. Its first live Qwen task was
  claimed and the first selected prospective judgment reached the evidence
  bridge, but graph ingestion rejected the new criticism status with
  `EpistemicGraphError: unknown structured criticism status`.
- The arm stopped without silently dropping the event or taking a subsequent
  unvalidated action. Its ledger and per-action checkpoints remain intact.
- Root cause: v1.9 added the typed cognition/bridge protocol
  `prospective-evidence-return`, but the authoritative graph reducer's closed
  structured-criticism vocabulary was not extended and the focused tests used
  fixture objects rather than the real reducer ingestion boundary.
- Any correction and rerun requires a new version. The minimal next preflight
  must add the status to the reducer vocabulary and prove real ingestion,
  replay, exact-chain selection, and revision-turn construction end to end.

## 2026-08-09 11:32:26 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- FAILED `generic_prospective/ar25/shared_live_qwen`: EpistemicGraphError: unknown structured criticism status.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
