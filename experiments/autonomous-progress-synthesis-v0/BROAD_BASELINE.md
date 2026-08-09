# Broad fallback lineage

The new progress workspace is layered over, not substituted for, the frozen
Reflector v164 symbolic policy.

Immutable development evidence:

- candidate: `candidate-df8025bb91c33a59`
- inference fingerprint: `1465a9b6ad8a4d1679e972126dea70d9b6be3128b471cb92278a67793aeedb66`
- candidate SHA-256: `be2aa3792cf8f0c8006f777fa88e7bee30ffcb55d206d30f46bf8715d89d64a8`
- packaged overlay SHA-256: `1a8c8ee04b3868f3edad5b65321d12b3b0fea72167b228bd338a1cb848e626b2`
- local official public-development score: `25.959943125184374`
- coverage: 62/183 levels, 5 complete games, 9,065 actions
- runtime: CPU, offline, 400 actions per game

This is public-development evidence, not a hidden Kaggle score. The source and
release package are retained in the sibling frozen release checkout. Before a
submission, they must be vendored byte-for-byte and re-hashed into the final
manifest.

## Non-regression rule

The broad policy always computes the same-state fallback first. Workspace
options begin with support zero. An option may spend a bounded probe only after
stagnation and may override control only after two direct prospective matches.
Any direct contradiction revokes the lease. Every override stores the original
fallback action and payload for exact counterfactual replay.

Consequently, adding Qwen changes attention and the hypothesis frontier; it
does not erase the broad controller or grant itself epistemic authority.
