# Qwen-to-R2 Generic Explanation Priors v0

## Question

Can one deterministic, game-blind Qwen prompt turn an anonymous R2 first-state description into an external relational explanation that R2 grounds and uses to improve real ARC-AGI-3 first-level control?

Qwen is an offline prior proposer. It is not an action policy, online planner, judge, or source of evidence.

## Information boundary

For each game Qwen receives exactly one structured initial state containing anonymous figure identifiers, structural descriptor classes, positions, pair relations, and opaque legal-action count. It receives no game ID, notes, recording trajectory, action meanings, reward, progress, known solution, or other game's state.

The instruction and JSON schema are byte-identical for every game. Temperature, seed, thinking budget, token cap, model hash, and server configuration are frozen. There is one request per game and no repair/retry after inspecting content. Invalid output becomes an abstention.

Every accepted hypothesis enters R2 as `externally-proposed` with zero empirical evidence. Only real target transitions can produce `externally-proposed-and-locally-confirmed` children. Qwen never receives those transitions.

## Hypothesis language

V0 deliberately supports a small generic pair-potential language:

- quantify over two to four anonymous figure variables constrained by current structural relations;
- prefer `decrease` or `increase` of translation-alignment residual for one variable pair;
- cite observed structural relations as support;
- require a target-local consequence confirmation before the prior can affect action choice.

The compiler rejects constants, unknown predicates, unsupported operators, invented relations, disconnected conditions, direct action choices, and malformed structures. It alpha-normalizes variables before schema identity is computed. Concrete entity IDs are used only by R2's local grounder and are never transferable schema identity.

## Cohort

Six first levels are selected before Qwen is called:

- `ar25`: known positive anchor for the already validated relational interface;
- `wa30`: source-nearest static analogy and causal-carrier stress case;
- `cn04`: zero-repeated-outline negative control;
- three games selected mechanically from distinct first-frame structural strata.

The exact mechanical rules and IDs are frozen in `selected_games.json` before inference.

## Arms

Every cohort game receives:

1. `scratch`: deterministic least-used opaque-action fallback;
2. `qwen_own`: that game's frozen Qwen proposal;
3. `qwen_mismatch`: a deterministically assigned different game's frozen proposal, which must structurally re-ground or abstain.

`ar25` additionally receives diagnostic `human_reference` and `self_built_reference` arms using the previously frozen successful schemas. These do not determine the main cross-game verdict.

All arms receive 32 actions, fresh environments, isolated controllers, atomic action checkpoints, and final ledger replay verification. Complex coordinate actions remain epistemic abstentions in v0. The anonymous state retains at most eight representative figures to keep every request inside the frozen 8K-token model context.

## Outcomes

Primary outcomes are first-level completion, actions to completion, and completed-level delta against scratch. Secondary outcomes are JSON validity, compiler acceptance, grounding, local consequence confirmation, prior-driven decisions, overrides, abstentions, and mismatched-prior behavior.

`PROMISING` requires Qwen-own to improve first-level completion or reduce successful action count by at least 25% in at least two games, with no completion regression on the negative control and at least one improvement outside ar25.

`ANCHOR_ONLY` means Qwen improves ar25 but no other game, without negative-control regression.

`NEGATIVE` means accepted, grounded Qwen priors cause aggregate completion regression or false intervention without any improvement. Otherwise the verdict is `INCONCLUSIVE`.

## Scientific interpretation

A good-looking explanation is not success. The causal chain must be inspectable:

```text
generic prompt → frozen Qwen JSON → validated hypothesis
→ R2 binding → target-local opaque-action consequence
→ action change → real level outcome
```
