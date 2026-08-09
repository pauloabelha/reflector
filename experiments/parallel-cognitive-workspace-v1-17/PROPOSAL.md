# Parallel Cognitive Workspace v1.17 — minimal transplant test

This experiment changes only the game and the scientific verdict from the
frozen, successful v1.16 architecture. Runtime cognition, prompt, ontology,
controller, compiler, action/probe budgets, Qwen schedule, context policy,
checkpoint protocol, and environment-evidence authority remain unchanged.

## Selection before perception

The parent freeze is commit
`77bc32cdb489b43c6cfa4787cc4cff8d95b30d61`. Eligibility is determined only
from installed environment metadata: exactly one `metadata.json`, game ID not
`ar25`, and tags exactly `["keyboard"]`. This guarantees compatibility with the
frozen simple-action transport without opening a frame or using an outcome.
The eligible IDs are `g50t`, `ls20`, `tr87`, and `wa30`. For each, compute
`sha256(parent_commit + "|" + game_id)` and select the smallest hexadecimal
score. The frozen winner is `wa30`, score
`6b6a120480452cdcf70bfc74a113ff38f44f003f591816b9e4e8b1e1bf8bb6bf`.

Selection uses no frame, recording, outcome, note, schema, or action meaning.
No change is permitted after opening the selected environment.

## Fresh paired run

- Arm A: frozen R2-only.
- Arm B: frozen v1.16 R2+Qwen shared workspace.
- Independently opened environments must have the same initial digest.
- Both arms retain the inherited 64-action budget.
- Both workspaces start empty. No ar25 object, schema, response, action model,
  history, note, or solution trace may enter either workspace.

## Transplant verdict

`PASS` requires every validity gate plus the complete live chain:

1. an initially ambiguous live Qwen schema grounding;
2. R2 prospective evidence from an intervention;
3. an evidence-citing non-alpha Qwen revision;
4. a uniquely grounded and prospectively confirmed revised binding;
5. at least one revised-control action different from same-state R2 fallback;
6. at least one exact same-state counterfactual where that action improves the
   already-declared relational potential over fallback.

Level completion is reported as `SCORE_PASS`, but is not required to establish
mechanism transplantation. A valid run missing any causal link is `FAIL`.
Unequal starts, leakage, transport/context failure, support-authority mutation,
identity/hash failure, or factual/counterfactual replay failure is `INVALID`.

No code, prompt, threshold, schema, or configuration repair is permitted after
the first selected-game environment is opened; another attempt would require a
new version.
