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
