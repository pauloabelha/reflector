# V2 requirement audit

This audit distinguishes implementation evidence from scientific outcome. The
system was implemented and the protocol was executed through its one permitted
blind attempt, but the milestone did **not** pass scientifically: blind role
discovery failed before a complete result set existed. The frozen verdict is
therefore `INCONCLUSIVE`.

## Specification sections 1–28

| Section | Status | Authoritative evidence |
|---|---|---|
| 1. Advance over V1 | Demonstrated on development/validation; unconfirmed blind | Evidence-derived two-edge diagrams and unfamiliar groundings in `learning/role_discovery.py`; blind prerequisite failure in `blind_results.json`. |
| 2. Scientific question | Executed with preregistered inconclusive rule | `preregistration/preregistration.json`, `aggregate_summary.json`. |
| 3. Synthetic family | Implemented | `evaluation/v2_game_family.py`, generated 9×13 game specs and manifests. |
| 4. Visual variation | Implemented and frozen | `generated_games/v2/*_manifest.json` and pair specs. |
| 5. False analogies | Implemented; exercised before blind | Development trace contains structural-near-match and reversed-relation probes; blind statistics unavailable. |
| 6. Splits | 4 development, 4 validation, 8 replacement blind pairs generated | `game_manifest.json`; contamination and replacement are disclosed in preregistration records. |
| 7. Same-k | Frozen independently | `preregistration.json.same_k`; generator tests. |
| 8. O/M/Q/R/E | Implemented with matched budgets | `frozen_configs/condition_manifest.json`; validation results. |
| 9. Overfit A | Executable schemas and replay implemented; no external LLM used | Candidate proposal budget is explicitly frozen at zero. This is a deliberate LLM-free scaffold limitation, not evidence of an LLM proposal loop. |
| 10. Compression | Implemented | Per-condition complexity metrics in validation results. |
| 11. Productive decomposition | Implemented on development evidence | Accepted intermediate/decomposition metrics and role-discovery tests. |
| 12. Equilibration | Implemented | Frozen objective weights and per-term equilibrium metrics. |
| 13. Composition/reification | Implemented and executable | Frozen Minds, composition/reification counts, quote/eval DSL tests. |
| 14. Level-B role discovery | Implemented but failed on at least one blind game | Masked transition inference; exact failure preserved in `blind_results.json`. |
| 15. Diagram correspondence | Implemented | Mapping scorer, two-edge tests, development and validation trace events. |
| 16. Active testing | Implemented and exercised | `v2_discriminating_correspondence_action` events in development run 003 reject false mappings. |
| 17. Evaluation phases | Implemented | Separate freeze, zero-shot, structural-probing, and accommodation trace phases. |
| 18. Minimal accommodation | Implemented | Closure checks, transactional Mind edits, complexity and regression fields. |
| 19. Genuine novelty | Implemented on validation | Validation pair 03 admits one counted S0 with conditional complexity 314 after closure checks. |
| 20. Three-level secondary analysis | Not implemented | Explicitly optional and not a prerequisite for the primary panel. |
| 21. Metrics | Implemented for completed pairs | `validation/run-001/results.json`; blind metrics correctly absent after failure. |
| 22. Aggregate analysis | Validation diagnostics complete; blind tables unavailable | `aggregate_summary.json` records empty blind tables rather than fabricated partial rows. |
| 23. Dashboard | Implemented | Live/replay server, V2 pair/condition/phase projections, 0.05× playback, latent hidden by default. |
| 24. Organization/commands | Implemented | README lifecycle commands and all named artifacts. |
| 25. Determinism/parallelism | Implemented for completed work | Process/serial equality tests and byte-identical validation rerun; immutable worker task boundaries. |
| 26. Order | Followed, with disclosed blind-seed amendment | Freeze preceded replacement blind generation and execution. No post-blind inference changes or rerun occurred. |
| 27. Acceptance | 15 criteria have implementation evidence; blind scientific completeness failed | Detailed criterion table below. |
| 28. Verdict | Emitted exactly as preregistered | `reports/final_report.md`. |

## Acceptance criteria 1–16

| # | Criterion | Finding |
|---:|---|---|
| 1 | Deterministic/replayable games | Proven by generator and replay tests. |
| 2 | No latent roles in observations | Proven by firewall tests and dashboard API check. |
| 3 | Two-edge causal chain | Proven by game-family and role-discovery tests. |
| 4 | Level A solved through schemas | Proven for all completed development and validation pairs; blind attempt failed while deriving a unique template. |
| 5 | Independently tested decomposition intermediate | Proven on development evidence and unit tests. |
| 6 | Evidence-inferred diagram equivalence | Proven by counterfactual evidence test; no equivalence registry is used. |
| 7 | Multi-edge correspondence evaluated | Proven in development and validation traces. |
| 8 | Discriminating action rejects false mapping | Proven by rejected structural-probe events in development run 003. |
| 9 | Frozen Mind attempts B before accommodation | Proven by event ordering in validation trace. |
| 10 | Matched budgets | Proven by frozen condition manifest. |
| 11 | Genuine novelty permits S0 | Proven by validation pair 03. |
| 12 | Prior regressions measured | Present for every completed condition; all were zero. |
| 13 | Blind only after freeze | Proven by create-once freeze and manifest hashes. |
| 14 | Aggregate M-versus-E | Validation reported; blind aggregate is correctly unavailable. |
| 15 | Verdict follows frozen rule | `INCONCLUSIVE` because 0 auditable valid blind pairs is below 6. |
| 16 | Results deterministic/replayable | Proven for completed panels; no successful blind result exists to replay. |

## Dashboard acceptance evidence

- Live full-board endpoint: `http://127.0.0.1:8770` during the audited run.
- V2 replay endpoint: `http://127.0.0.1:8771` during the audited run.
- Live episode: 41 actions, 324 canonical events, final score 4.
- Saved live replay: `artifacts/live/current-board-trace.json`.
- The live JSONL events and saved replay events are exactly equal.
- V2 replay exposes 78 recorded board transitions over 4 pairs and 5 conditions.
- The default V2 API payload contains no `posthoc_latent` field.

## Scientific conclusion

The development and validation data are encouraging but cannot support the
primary hypothesis. The one allowed blind run exposed a real generalization
failure in visual-role-template uniqueness. Preserving that failure without a
post-hoc patch or rerun is the protocol-correct outcome.
