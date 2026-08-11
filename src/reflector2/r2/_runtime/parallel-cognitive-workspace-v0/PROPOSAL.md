# Parallel Cognitive Workspace v0

## Claim

Can a fast grounded Reflector process and a slower semantic Qwen process improve real ARC control by concurrently maintaining one executable epistemic workspace, while confirmation and refutation remain grounded exclusively in chronological interaction?

This is not a teacher–student pipeline. R2 does not send a finished problem to Qwen and wait for an answer. Qwen does not act as policy or judge. Both maintain versioned epistemic objects in one live workspace. R2 continuously emits grounded deltas; Qwen asynchronously proposes abstractions and experiments; the environment adjudicates their predictions.

## Processes and authority

- **R2 loop:** perceives; builds ordinary R2 schemas, bindings, shadows, transition morphisms, and episode explanations; calibrates opaque effects; acts; and posts compressed deltas.
- **Qwen loop:** consumes a compressed canonical workspace plus unseen deltas; maintains a rolling interpretation; and posts proposed schemas, explanations, counterfactuals, missing relations, or discriminating experiments.
- **Environment arbiter:** is the sole action committer and evidence authority. It validates proposal basis revisions, grounds executable schemas, and records real consequences.

Every object carries author, basis revision, uncertainty/status, lineage, and evidence links. Similar R2- and Qwen-authored schemas retain distinct provenance even when they converge.

## Concurrency

Qwen v0 inference takes tens of seconds while an unpaced R2 episode takes seconds. Each Qwen call therefore receives a frozen basis revision while R2 may advance through a bounded two-action parallel window. At the window boundary, R2 synchronizes rather than finishing the episode before the semantic worker can contribute. Late proposals are never applied by age alone: generic schemas may re-ground against the current observation, while situated explanations and experiments require basis-compatible entities and intervention history.

Qwen receives at most four calls per episode, at frozen action-count triggers 0, 4, 8, and 12. A response becomes logically eligible four actions after its source observation; the arbiter waits at that boundary if inference is unfinished. This makes results independent of GPU scheduling while preserving a real four-action interval in which R2 and Qwen work simultaneously. “Continuous” means a persistent event-driven worker over the episode—not an unbounded call on every frame.

## Staged experiment

### Gate A — offline workspace replay

Replay the frozen 17-action ar25 Qwen-own trace into the new reducer. The hash chain, canonical state, provenance, confirmations, action sequence, and terminal level must reconstruct deterministically across repeated runs.

### Gate B — deterministic workspace injection

Post the frozen successful Qwen ar25 proposal into a fresh live workspace, then run R2 through the new arbiter. It must complete ar25 level 1 in at most 17 actions with full replay verification. This tests the bus and control integration independently of fresh language-model variance.

### Gate C — live parallel ar25

Run the resident Qwen worker and R2 concurrently from the generic initial workspace. Qwen sees R2's compact schema/explanation/effect stream and may update proposals at the frozen triggers. The architecture passes development if it completes level 1 within 22 actions (the ceiling of 1.25 times the 17-action reference). At least one post-initial Qwen request must be processed, every influential proposal must have target-local post-activation confirmation, and at least one Qwen-confirmed decision must differ from the same-state no-Qwen recommendation. A no-Qwen workspace arm must share the same R2/workspace implementation and action budget.

Only after these gates is the complete code, prompt, configuration, and ar25 development result hashed into a cross-game freeze manifest.

### Held-out evaluation

Run the unchanged architecture on `cd82`, `wa30`, and `cn04`. Primary arms are the identical workspace with no Qwen writer, the frozen one-shot v0 own-game proposal, and live parallel Qwen. After primary outcomes are frozen, replay the live proposal ledgers with a four-action additional delay and with cyclically shuffled cross-game proposal sources. These secondary controls test timing and semantic specificity without further Qwen calls.

## Verdicts

- `ONLINE_PROMISING`: all ar25 gates pass and live Qwen improves over both no-Qwen and one-shot arms on `cd82` or `wa30`, with a causal contribution from a post-initial proposal, no `cn04` regression, exact frozen-ledger reinjection, and no comparable shuffled gain.
- `ANCHOR_ONLY`: all ar25 gates pass, but no held-out game improves and the negative control does not regress.
- `ANCHOR_FRAGILE`: deterministic injection passes but fresh parallel Qwen fails the ar25 acceptance bound.
- `NEGATIVE`: the workspace breaks deterministic reproduction, causes held-out regression, or admits stale/unvalidated proposals into control.
- `INCONCLUSIVE`: transport/environment failure prevents the preregistered comparison.

## Interpretation boundary

The executable vocabulary is still designer-supplied. A positive result shows cooperation through a shared falsifiable workspace and Qwen's selection/composition of R2 concepts. It does not show unconstrained concept invention. No game ID, notes, semantic game labels, known solution, reward interpretation, or future outcome enters Qwen cognition.
