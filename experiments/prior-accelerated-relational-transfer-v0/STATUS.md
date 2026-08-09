# Prior-Accelerated Relational Transfer v0 — Live Status

This file is the human-readable checkpoint log. Machine state is written atomically under `artifacts/checkpoints/` during execution.

## 2026-08-08 — Branch and scope checkpoint

- Branch: `prior-relational-transfer-v0`, created from `control` at `d4c04e9`.
- Isolation: all new implementation and artifacts remain in this experiment directory.
- Core changes: none.
- Real environments: required; no synthetic ARC substitutes count toward the result.
- Source: `ar25`, first level only.
- Planned target arms: scratch, transferred self-built schema, external prior, and combined.
- Planned targets: one mechanically selected structural match and one mechanically selected negative control.
- Budget: at most 32 actions per target arm.
- Provenance must remain explicit: self-built, transferred-self-built, externally-proposed, externally-proposed-and-locally-confirmed.
- Current phase: auditing the existing harness and structural representation before freezing the executable preregistration.

## 2026-08-08 — Selector representation checkpoint

- Coarse R2 audit: the literal `InteriorContrastCount` rule would select `tr87`; it reports `wa30` as six same-interior pairs and zero different-interior pairs.
- Diagnosis: contrast count discards spatial layout. In `wa30`, repeated figures have the same contrast count but different normalized contrast-cell positions.
- Design correction, made before any target execution: compose the already available figure/cell/value structure into a palette-invariant interior-layout signature and select the source-nearest qualifying relational group.
- The failed coarse counts remain in `selected_targets.json` for audit; no game is selected by name or by outcome.

## Checkpoint policy

- Write one atomic machine checkpoint after every real action.
- Update this file at each completed phase and with partial arm results during long runs.
- Commit experiment code/design milestones to this branch without adding unrelated untracked work.

## 2026-08-08 — Frozen pre-run checkpoint

- Positive target: `wa30`; source distance: `[1, 1, 0, 1]`.
- Negative target: `cn04`.
- Self-built schema admitted with 16 chronological source transitions.
- Source action identities are present only in the audit and absent from transferred schema identity/control.
- No target action had been executed when `FROZEN_MANIFEST.json` was written.

## 2026-08-08 — Live run started

- Eight real-game arms launched with up to 4 isolated workers.
- Per-action machine progress: `artifacts/progress/`; recoverable ledgers: `artifacts/checkpoints/`.
- Partial arm: `positive/wa30/combined` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.
- Partial arm: `positive/wa30/external` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.
- Partial arm: `positive/wa30/self_transfer` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.
- Partial arm: `positive/wa30/scratch` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.
- Partial arm: `negative/cn04/external` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.
- Partial arm: `negative/cn04/combined` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.
- Partial arm: `negative/cn04/scratch` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.
- Partial arm: `negative/cn04/self_transfer` completed with actions=32, levels=0, prior_decisions=0, replay_verified=True.

## 2026-08-08 — Live run complete

- Verdict: `INCONCLUSIVE`.
- All final ledgers replay-verified: `True`.

## 2026-08-08 — Primary diagnostic interpretation

- `wa30`: scratch, self-transfer, external, and combined all ended at 0 levels after 32 actions.
- The relational antecedent was visible, but no observed target action instantiated the source's coupled-mover role: 0 local confirmations and 0 prior overrides.
- All four `cn04` negative-control arms were behaviorally identical, as required; no regression.
- Smallest gap: select and bind the causal carrier, not merely the nearest static repeated-form group.

## 2026-08-08 — Secondary fresh-ar25 sanity result

- This sanity pair was run after the primary result and does not change its `INCONCLUSIVE` verdict.
- Scratch: 0 levels in 32 actions.
- Self-transfer: completed level 1 in 17 actions.
- External prior: completed level 1 in 17 actions.
- Combined: completed level 1 in 17 actions.
- Each successful arm made 14 prior-driven decisions after local opaque-action calibration and reached residual 0.
- Every secondary ledger replay-verified exactly.
- Interpretation: the action-agnostic relational schema is a viable input interface for solving ar25 level 1; cross-game causal-role binding remains unsolved.
