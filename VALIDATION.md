# Reflector validation protocol

This protocol was fixed before the first full diagnostic run. Its purpose is
to expose failure, not to manufacture an ARC score.

## Claim boundary

`reflector validate` is a deterministic suite of synthetic interactive
mechanism tests. It is not ARC-AGI-3, does not estimate leaderboard accuracy,
and does not replace the required run over 25 official public games. The
official public evaluation remains gated on an accepted data license and
`ARC_API_KEY`.

## Fixed suite

Thirty paired seeds are run for four families:

- invariant control: discover and reuse one control across changing scenes;
- contextual control: learn four recurring scene-to-control mappings;
- rare-object click: ground a complex action on a visual object;
- temporal sequence: discover and reuse a three-action sequence.

Each run has a fixed action budget and a known oracle minimum. The report keeps
completion, win rate, actions, and completed-run efficiency separate.

The deployed `SymbolicPolicy` is compared with:

- the same policy without reflecting abstraction;
- the same policy without planning;
- a minimal symbolic ablation;
- a context-free score-only bandit;
- a full-frame context table;
- the rare-color heuristic alone;
- seeded random actions.

## Preregistered support criteria

All emitted actions must be legal. The full system must beat seeded random and
the score-only controller on paired completion with a 95% bootstrap interval
strictly above zero. Reflecting abstraction must causally improve paired
efficiency over the no-abstraction agent. Full-policy contextual completion
must be at least 0.75 and rare-object-click completion at least 0.95.

The central causal thesis is supported only if all four comparative and
generalization criteria pass. A useful isolated mechanism with failed causal
criteria is reported as mixed; legality, determinism, or basic performance
failure is reported as not supported.

Seeds 0–29 exposed two implementation defects during development: identical
frames were skipped after a new action, and global plans overrode negative
evidence in the current context. After those fixes, seeds 10,000–10,029 were
reserved as an untouched confirmation set. No mechanism or threshold may be
changed after viewing that confirmation result.

Run:

```bash
.venv/bin/reflector validate --seed-start 10000 --seeds 30 \
  --output validation-results-holdout.json
```

The JSON includes every run and a SHA-256 digest of the canonical result.
