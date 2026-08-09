# Shared Attention Census v1

## Decision and rationale

The next experiment should stop optimizing ar25 and perform a breadth-first diagnostic census over the complete 25-game public corpus.

V0 established safe concurrent transport, deterministic replay, frozen-schema compatibility, and a real sequence of Qwen schema revisions. It did not establish shared cognition: Qwen operated over bounded reconstructed projections and never produced a uniquely bound live schema. Continuing to tune that interface against ar25 risks replacing architectural discovery with game-specific adaptation.

V1 therefore freezes one generic mechanism and asks where, if anywhere, bidirectional cognitive pickup appears naturally. ARC score is secondary. The primary object of study is whether R2 and Qwen lift epistemic objects into one another's active frontiers and whether those pickups cause grounded downstream work.

## Constitutional invariant

There is exactly one authoritative evolving epistemic graph.

R2 runtime state and Qwen context are disposable caches reconstructed from that graph. Neither is an independent world model and neither may contain authoritative knowledge absent from the workspace.

Workers may spend computation to alter attention. Only environment evidence may alter epistemic support.

Consequently:

- Qwen may propose schemas, explanations, questions, analogies, or attention contributions. These begin with zero empirical support.
- R2 may propose schemas, bindings, explanations, shadows, or attention contributions. These also begin without support unless linked to already committed environment evidence.
- A worker contribution may raise salience but cannot claim confirmation.
- The environment arbiter alone commits actions and evidence events.
- The reducer alone computes aggregate support, salience, lifecycle, and worker frontiers from immutable events.

## Workspace layers

### Immutable event ledger

Every environment transition and cognitive mutation is an immutable hash-chained event. Each isolated `(game, arm, profile)` workspace has its own ledger, blobs, cursors, action checkpoints, and replay verification. Parallel workers never append to the same file without the workspace commit lock.

### Materialized epistemic graph

The authoritative graph contains stable, versioned objects and edges:

- schemas and schema derivations;
- bindings and all still-live competing bindings;
- explanations and dependency graphs;
- shadows and predictions;
- evidence, confirmations, contradictions, and refutations;
- correspondence histories;
- open questions and expansion requests;
- action proposals and committed action provenance;
- attention contributions;
- provenance and causal basis for every object.

No lossy label such as `ambiguous` may replace the live competing binding set. Such a label may be a cached aggregate only when every alternative remains reachable.

### Active frontiers

Belief and attention are distinct.

`support(x)` is an evidence-derived epistemic quantity shared by all workers.

`attention_i(x,t)` is the value of worker `i` examining object `x` now. R2 and Qwen use different deterministic scoring biases over the same graph.

R2 attention emphasizes grounded binding stability, prediction accuracy, causal repetition, cheap tests, and immediate control relevance. Qwen attention emphasizes unresolved alternatives, explanatory tension, novelty, abstraction opportunity, discriminative value, and recent changes.

Frontiers are selected under root and token budgets, then expanded to mandatory dependency closure. If a root's closure does not fit, the whole lower-value root cluster is evicted. A live competing alternative may never be silently removed from a selected ambiguity cluster.

### Qwen working context

Qwen context is a bounded cache, never truth. It receives:

1. a stable generic cognitive contract;
2. once per workspace epoch, a complete compact orientation/materialization;
3. the current dependency-closed Qwen frontier;
4. every lossless ordered delta since its durable cursor;
5. requested expansions addressed by stable object ID.

Settled history may be compacted into addressable summaries. Still-live alternatives, dependencies, contradictory evidence, and unresolved derivations must remain losslessly recoverable. Each rendered context records token occupancy, repeated-token estimate, objects included/omitted, dependency closure, cursor range, and expansion provenance.

The Qwen server is shared and GPU-resident, but Qwen cognition is workspace-isolated. A durable global request queue serializes inference. A response is committed to its source workspace before the queue advances. Hidden KV or conversation state is an optimization only; restart reconstructs cognition from the workspace cursor and stored semantic orientation.

#### Direct world interface

Qwen and R2 receive the world in parallel. Every Qwen turn includes the current visual frame. After the first intervention it also includes the immediately preceding frame, the anonymous intervention reference, and the current frame as an ordered transition. A bounded number of older transitions may be retrieved by epistemic salience when they confirmed/refuted a live claim or caused a large structural change. The complete frame/transition history remains content-addressed and expandable; it is never reconstructed solely from R2 prose.

ARC action IDs and semantic direction labels remain outside Qwen's control interface. The visual transition names an episode-local opaque intervention model, allowing causal comparison without letting Qwen emit environment commands.

#### Observable grounding invariant

Every situated Qwen explanation must either terminate in observable region/component addresses or expose an explicit open grounding port for R2. Region objects carry a frame reference, bounding box, mask blob/RLE digest, component identity, and perceptual descriptors. Temporal groundings additionally cite ordered before/after frame and transition IDs. R2 alone adjudicates whether a proposed grounding is bound, ambiguous, open, impossible, or contradicted.

The executable chain is `pixels <-> regions/correspondences <-> bindings <-> schemas <-> explanations`. Generic schema objects need not contain coordinates, but any situated explanation or control-relevant binding must have a dependency path to observation-grounded objects.

#### Context compression policy

The authoritative layer is lossless: hash-chained events, content-addressed PNG frames, RLE masks, stable object IDs, correspondence/evidence edges, and the complete action ledger. The Qwen rendering uses short deterministic aliases, interned predicate vocabulary, current/recent images, compact graph deltas, and a dependency-closed salient cut.

Small-lossy semantic compaction is permitted only for dormant or resolved payload bodies. Their stable ID, kind, support, dependency topology, payload hash, omission reason, and expansion handle remain visible. Live competing bindings, open grounding ports, rejection witnesses, and causal evidence paths may not be compacted away. Periodic visual keyframes plus lossless changed-cell/region deltas avoid resending the visual history.

## Salience model

Workers write immutable attention contributions rather than assigning final salience directly:

`AttentionContribution(worker, object, reason, magnitude, basis, created_at, expiry)`.

The reducer computes worker-specific attention from common factors:

- empirical support;
- predictive power;
- control relevance;
- uncertainty and grounding ambiguity;
- recent score/evidence change;
- discriminative value;
- semantic novelty or compression;
- worker proposal boost;
- complexity and dependency cost;
- age/decay.

Proposal boosts are bounded, provenance-visible, and decaying. Alpha-equivalent or paraphrastic objects share a novelty cluster so repeated proposals cannot accumulate attention by duplication.

## Bidirectional pickup

A pickup is not mere visibility.

### Qwen to R2 pickup

A Qwen-authored object crosses R2's cutoff and subsequently causes at least one new grounded R2 operation: binding enumeration, shadow projection, explanation refinement, discriminating test, or changed action proposal.

Primary count:

`N_QR = number of distinct Qwen objects with grounded downstream R2 work`.

### R2 to Qwen pickup

An R2-authored object newly crosses Qwen's cutoff and Qwen subsequently cites it while producing a non-alpha-equivalent schema, explanation, question, counterfactual, abstraction, or attention reallocation.

Primary count:

`N_RQ = number of distinct R2 objects causing cited downstream Qwen work`.

Visibility, citation, pickup, grounding, prediction, confirmation, and action influence are recorded as separate edges. This prevents a paraphrase from being counted as cognitive transfer.

## Strong causal chain

The strongest successful chain is:

`Qwen proposal -> R2 pickup -> unique grounding -> prospective prediction -> later environment confirmation -> control improvement`.

Every edge must cite an earlier committed object/event. Confirmation is invalid if the prediction was written after the relevant transition. Control improvement is assessed against the paired R2-only arm, never against a known solution trace.

## Corpus and arms

The frozen corpus is the 25 games locally present in the public reflector-v14 recording set:

`ar25, bp35, cd82, cn04, dc22, ft09, g50t, ka59, lf52, lp85, ls20, m0r0, r11l, re86, s5i5, sb26, sc25, sk48, sp80, su15, tn36, tr87, tu93, vc33, wa30`.

For every game:

- `r2_only`: shared graph, reducer, R2 attention policy, arbiter, and budget; no Qwen writer.
- `shared_attention_qwen`: identical fresh start plus the Qwen worker and Qwen attention policy.

No previous actions, rewards, notes, semantic labels, known solutions, or another game's cognitive objects enter either arm. Game IDs are transport metadata and are omitted from Qwen content.

Both arms are run from a fresh environment for every `(profile, game)` pair. This yields three profile-matched R2-only controls rather than reusing one trajectory across profiles, so scheduling, checkpoint, and frontier-policy effects remain paired and auditable. Environment initialization and action/replay protocol are identical within each pair.

## Global architecture profiles

There are three frozen, non-game-specific profiles:

- `balanced` (primary): 12 frontier roots, 2,400 compact-renderer token units, proposal boost 1.0, 12-action half-life.
- `wide_frontier`: 24 roots and 3,200 compact-renderer token units; other balanced parameters unchanged.
- `persistent_proposal`: balanced frontier with boost 2.0 and 24-action half-life.

These are diagnostic sensitivity profiles, not a leaderboard search. No per-game selection is permitted. The primary scientific verdict uses `balanced`; the other profiles localize frontier-capacity versus attention-persistence bottlenecks.

## Runtime and concurrency

- Action budget: 32 per arm.
- Qwen calls: at most three per treatment episode, triggered at committed action counts 0, 8, and 16.
- ARC concurrency: at most four isolated environment workers, scheduled by game.
- Qwen concurrency: one durable global FIFO queue feeding the single resident GPU server.
- Each job is independently resumable from its action ledger and epistemic cursor.
- Each committed action writes pending and committed checkpoints with predecessor/successor observation digests.
- The parent scheduler alone writes the aggregate census state.

The frozen census contains 25 games × three profiles × two arms = 150 fresh episodes (75 pairs), at most 4,800 environment actions and 225 Qwen calls. The measured-v0 estimate is 3.45 serial GPU hours, 4.52 central wall-clock hours with four environment workers, and 5.19 hours after a 15% census allowance; the operational range is 5–7 hours. The run is therefore suitable for an overnight census.

## Recorded measurements

Per object:

- author and provenance;
- type, canonical identity, dependencies, and lineage;
- support trajectory with evidence links;
- R2 and Qwen attention trajectories and score components;
- frontier entry/exit events for each worker;
- pickup/citation/grounding/prediction/confirmation/refutation/action-influence edges;
- complexity, age, proposal boost, and decay.

Per episode:

- R2- and Qwen-authored schema/explanation counts;
- `N_QR`, `N_RQ`, and complete causal chains;
- confirmed/refuted/expired shadows;
- actions, levels reached, levels completed, and exact replay status;
- Qwen calls, input/output tokens, latency, context occupancy, repeated-token fraction, expansions, and expansion utility;
- Qwen novelty classification: ahead of R2, refinement, paraphrase, inert, or harmful.

Across paired arms:

- completion and level deltas;
- action delta when both complete the same level extent;
- peak-level regressions;
- changed same-state actions attributable to supported Qwen-derived objects;
- mechanism incidence independent of score.

## Outcome buckets

- **A — Cognitive transfer plus score gain:** at least one complete grounded Qwen-to-R2 causal chain and paired improvement without an offsetting hard regression.
- **B — Cognitive transfer without score gain:** grounded bidirectional pickup occurs, but levels/actions do not improve.
- **C — Proposal without R2 pickup:** Qwen creates non-paraphrastic objects, but none crosses the R2 frontier and causes grounded work.
- **D — No meaningful Qwen novelty:** outputs are empty, invalid, duplicates, paraphrases, or uncited restatements of the rendered frontier.

`HARMFUL` is additionally recorded when treatment reaches fewer levels than baseline, causes unsupported action influence, crowds a supported R2 object out of the dependency-closed frontier, or substantially increases actions when both arms complete.

## Preregistered primary verdict

The architecture is `MECHANISTICALLY_PRESENT` if the balanced profile produces at least one Qwen-to-R2 grounded pickup and at least one R2-to-Qwen cited non-paraphrastic pickup across two or more distinct games, with zero support-authority violations and exact replay for every counted episode.

It is `CONTROL_PROMISING` if, in addition, at least one balanced-profile game falls in bucket A and no more than one game has a hard level regression.

It is `ATTENTION_BOTTLENECK` if meaningful Qwen novelty exists but pickups occur only in wide/persistent sensitivity profiles.

It is `REPRESENTATION_OR_MODEL_BOTTLENECK` if the balanced and sensitivity profiles remain in C/D despite valid contexts and successful Qwen transport.

Any support mutation not causally linked to a committed environment evidence event, any future leakage, or any failure to replay a counted causal chain invalidates the corresponding result.

## Freeze and leakage boundary

Before the first v1 ARC action, hash and freeze:

- this proposal and configuration;
- graph/reducer/frontier code;
- R2 and Qwen worker code;
- prompts and response schemas;
- model/server configuration;
- complete game list;
- action/Qwen budgets and scheduler policy;
- environment package hashes.

After freeze, no prompt, score weight, cutoff, graph rule, controller rule, or profile may change based on any game result. Failures are recorded and resumed; they are not repaired in place. The census may be rerun only under a new versioned experiment.
