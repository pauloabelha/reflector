# Parallel Cognitive Workspace v1.15 status

## 2026-08-09 — freeze ready

- v1.14 is preserved as INVALID after its first confirmed revised-control
  transition because an unchanged probe packet attempted to reuse a criticism
  identity with a newer grounding payload.
- v1.15 changes only that criticism lifecycle: unchanged packet means reuse;
  novel packet means a new immutable criticism.
- No v1.15 ARC environment has been opened and no fresh-workspace Qwen request
  made.
- The preserved v1.14 action-25 prefix reproduces the collision exactly. With
  the v1.15 adapter installed, the unchanged packet is recognized by its frozen
  criticism key and the renderer is not called; the already-committed control
  evidence remains present in the graph.
- A synthetic additional probe-evidence fixture changes the packet/key and
  proves that a genuinely novel criticism is still created. Mixed-schema
  filtering and idempotent installation are covered.
- Twenty-two v1.14/v1.15 tests pass. Dry-run manifest construction, Python
  compilation, and `git diff --check` pass. No controller, Qwen prompt, schema,
  action budget, or causal gate changed.

## 2026-08-09 13:14:45 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=64, Q→R grounded=0, replay=True.
- FAILED `generic_prospective/ar25/shared_live_qwen`: LedgerError: unsupported event type: CounterfactualBranchVerified.

## 2026-08-09 — factual breakthrough, verifier-invalid result

- The shared arm **completed ar25 level 1 in 38 actions**. The fresh R2-only arm
  remained at level 0 after 64 actions. The full factual trajectory was committed
  before post-episode analysis, and the factual replay routine returned without
  mismatch.
- The causal chain is durable: two Qwen-to-R2 grounded pickups; four ambiguity
  probes; eight initial supported predictions; an evidence-citing non-alpha
  Qwen revision to `SameInteriorLayout -> Decrease
  TranslationAlignmentResidual`; one unique `f01/f02` binding; one supported
  confirmation probe; then confirmed prospective control. The final control
  chose opaque intervention 3 over fallback 5 and predicted residual 6 -> 0;
  the committed successor reported `levels_completed=1`.
- Control reduced the selected residual monotonically from 84 to 0. The shared
  graph ended with 18 environment support edges and zero authority violations.
- v1.15 is nevertheless **INVALID for the full binary scientific gate**. The
  post-episode counterfactual code successfully opened/replayed branch
  environments, then attempted to append the already-designed event type
  `CounterfactualBranchVerified`. That type was missing from the ledger's
  `EVENT_TYPES` allowlist, so result assembly stopped before counterfactual
  attribution could be durably recorded.
- Required successor change is only the ledger protocol repair: admit the
  coordinator-authored counterfactual verification event and test its durable
  replay. No cognition, prompt, schema, controller, or environment behavior may
  change.
