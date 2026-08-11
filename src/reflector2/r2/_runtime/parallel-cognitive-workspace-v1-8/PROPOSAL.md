# Parallel Cognitive Workspace v1.8

v1.8 is the separately versioned replacement for v1.7's serving-context
infeasibility. All cognitive, controller, prompt, frontier, action, call,
completion, and binary-gate settings remain unchanged.

The sole scientific change is a global Qwen context window of 24,576 tokens
instead of 16,384. The v1.7 evidence-bearing requests measured 16,107, 20,499,
and 19,412 prompt tokens. Each therefore fits the new window together with the
unchanged 2,048-token completion reserve. No game-specific content, schema,
explanation, trace, note, or outcome is introduced.

The server must report `n_ctx=24576` before either fresh environment is opened.
The original v1.4 binary gate remains authoritative: a breakthrough requires a
live proposal, grounding, prospective environmental evidence, a non-alpha
Qwen revision citing that evidence, confirmed revised-schema control, a
favorable exact same-state counterfactual, and ar25 level-1 completion.

