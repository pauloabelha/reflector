# Broad shared policy v0

## Objective

Beat the frozen hidden Kaggle baseline without discarding it. The treatment is
the exact v164 broad symbolic policy plus one shared epistemic workspace and
environment-leased option control.

## Immutable baseline

- candidate `candidate-df8025bb91c33a59`
- candidate SHA-256 `be2aa3792cf8f0c8006f777fa88e7bee30ffcb55d206d30f46bf8715d89d64a8`
- inference fingerprint `1465a9b6ad8a4d1679e972126dea70d9b6be3128b471cb92278a67793aeedb66`
- Kaggle submission `55226491`, complete, public score `0.02`
- local public-development score `25.959943125184374`, 62/183 levels

The later trace-only v168 submission scored `0.01`; therefore v164, not v168,
is the fallback lineage.

## Mechanism

For every live state:

1. v164 computes its ordinary same-state action and cognitive event first.
2. The environment observation, recent transition, R2 event, live option
   frontier, evidence, and prior decisions inhabit one workspace.
3. R2 or Qwen may create support-zero goal/options and raise attention.
4. When v164 has made no progress for eight decisions, the least-tested viable
   option may spend one of eight typed probes.
5. Two direct prospective outcome matches grant that exact situated option a
   control lease. One contradiction revokes it.
6. Every changed decision stores v164's action and full payload for exact
   same-state counterfactual replay.

Attention never changes support. Qwen never writes evidence. The environment
is the sole empirical authority.

## Generic option families

- assignment/placement, coverage, and terminal service;
- relational/compositional gradient potentials;
- conditional route/navigation;
- collection/transport with explicit OPEN roles;
- symbolic transformation from visual examples;
- editable topology via bounded observed-state search.

No runtime branch may inspect a game identifier. Situated IDs, coordinates,
opaque actions, frames, and evidence never enter a transferable goal AST.

## Gates before a hidden submission

1. Empty-option wrapper is action/digest identical to v164.
2. All option families pass synthetic permutation, palette, translation, and
   opaque-action relabeling tests.
3. Public development has no hard level regression versus v164 and exact replay
   holds for every treatment trajectory.
4. Every treatment override has a complete proposal→prediction→transition→
   evidence→lease→decision lineage and a favorable same-state counterfactual.
5. The final offline notebook contains the exact v164 fallback and requires no
   network or unavailable model.

The first hidden submission after these gates is a single frozen attempt. No
post-result game diagnosis may modify the same version.
