# Parallel Cognitive Workspace v1.16

v1.16 is a separately versioned replacement for the post-completion verifier
failure in v1.15. It inherits the factual environment, cognitive workspace,
Qwen, controller, action/probe budgets, and every causal gate unchanged.

The sole repair admits the coordinator-authored
`CounterfactualBranchVerified` record to the hash-chained ledger. The event was
already produced by the frozen post-episode analyzer, but omitted from the
ledger type allowlist. Its payload records the decision index, content-addressed
branch blob, exact actual-branch replay flag, and favorable flag.

No v1.15 schema, response, workspace, controller state, action ledger, notes, or
solution trace may seed either fresh v1.16 arm. Preserved artifacts are used
only to regress the post-episode verifier.
