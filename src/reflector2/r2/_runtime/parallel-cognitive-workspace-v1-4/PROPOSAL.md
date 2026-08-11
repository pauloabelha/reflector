# Parallel Cognitive Workspace v1.4

## Frozen question

Can a fresh, generic shared-cognition controller solve public `ar25` level 1
because a live Qwen proposal is prospectively tested, revised from returned
evidence, confirmed, and then used by R2 control?

This is one binary paired experiment. It is not another census and it is not a
prompt-tuning loop. There are exactly two arms:

- `r2_only`
- `shared_live_qwen`

Both use the same revised R2 controller and independent fresh environments.
The shared arm's only additional input is live Qwen output produced during that
arm. No frozen proposal, external schema, explanation, note, prior cognitive
object, or solution trace is allowed.

## Frozen execution

The environment revision, code, config, prompt, response schema, reducer,
model file and hash, quantization, server parameters, and seed are frozen
before either environment is reset. Both arms must have the same initial
observation digest. Neither arm may inspect the other arm while running.

Each arm has one worker, with at most two ARC workers total, so the pair may run
concurrently. Qwen transport is serialized and belongs only to the shared arm.

- Environment-action budget: 48 per arm.
- Level target: first completion of level 1.
- Qwen-call budget: four.
- Eligible Qwen boundaries: actions `0, 12, 24, 36`, with deterministic
  integration exactly eight logical actions later. The initial proposal is
  integrated at action 8; actions 8–11 are therefore available for prospective
  probing before the evidence-bearing action-12 request is constructed.
- Context window: 16,384 tokens, including a hard 2,048-token reserve.
- Maximum completion: 2,048 tokens, including at most 1,024 thinking tokens.
- Per-call timeout: 180 seconds.
- Probe budget: at most five R2-selected probe decisions: at most four over an
  ambiguous population and one confirmation probe for a later unique revision.
- Qwen-influenced control budget: at most 24 decisions. Counterfactual audit is
  capped at the first eight decision points plus one contiguous influenced
  suffix, so the audit cost is bounded without preventing a multi-step policy.

The single `generic_prospective` frontier is fixed at 24 roots and 6,400
frontier units. It is an architecture-wide dependency-closure budget, not an
`ar25`-specific salience rule. If its mandatory causal closure cannot fit the
context gate, the result is `INVALID`; the budget is not enlarged in place.

## Isolation and leakage boundary

The shared arm begins with no externally authored cognitive object. Its Qwen
request may contain only the generic prompt and the dependency-closed live
epistemic graph built in the fresh episode. The game identifier is transport
metadata and is omitted from Qwen content. Environment actions and action-like
tokens are forbidden in both requests and responses.

The following inputs are prohibited:

- frozen Qwen proposals;
- external schemas or explanations;
- user notes, including ARC or `ar25` notes;
- known solutions, action traces, rewards, or future recording outcomes;
- another game's cognitive objects;
- cognitive objects or learned controller state from an earlier run.

Existing artifacts may be used only before freeze as read-only codec, replay,
and integrity-test fixtures. They may not determine semantic content,
controller weights, action preferences, thresholds, or live prompts.

## Prospective cognition loop

### 1. Live proposal and grounding

Qwen may write a variable-only schema, a situated explanation over visible
stable IDs, attention contributions, or an expansion request. Qwen may not
choose or describe an environment action and may not assert support.

R2 grounds a proposed schema against the current live graph. An unbound or
ambiguous schema cannot affect control. Its full competing-binding witness is
committed as structured criticism.

### 2. Prediction before probe

For a uniquely bound schema, R2 may select a legal probe with a frozen generic
information/control score. The probe is R2's decision, not Qwen's. Before the
probe executes, R2 must commit an immutable prospective prediction containing:

- the exact pre-state observation digest;
- schema and binding IDs;
- the bound effect pair;
- an opaque intervention ID;
- the current residual and predicted direction of change;
- a one-action horizon and expiry revision.

A prediction written after its transition is invalid. Probe actions are marked
as exploration and cannot themselves claim a policy improvement.

### 3. Evidence return

The environment commits the transition and measured residual. The reducer,
not Qwen or R2, links the prediction to an `evidence_return` and emits the
confirmation, refutation, or expiry result. Only environment evidence may
change empirical support.

The next eligible Qwen request pins the exact causal unit without lossy
substitution:

`derivation -> schema -> binding/criticism -> prediction -> transition -> evidence verdict`

### 4. Non-alpha revision

After an ambiguous grounding or refuted prediction, an alpha-identical schema
is rejected. A revision counts only if its canonical relational conditions or
consequence change and its basis cites the criticism or evidence witness.
Explanatory paraphrase is not revision. If the visible vocabulary cannot
support a defensible revision, Qwen must request expansion or abstain.

Two consecutive rejected alpha repeats or abstentions stop further Qwen calls;
R2 continues to the ordinary arm stop. If a criticism or refutation occurred,
the binary `PASS` gate requires at least one accepted non-alpha revision.

### 5. Revised R2 control

At every state, R2 first records the action its frozen no-Qwen controller would
take. This is the same-state fallback. A Qwen-derived schema may change a
post-probe control decision only when it is uniquely bound and has at least one
prospective confirmation. The decision must cite its complete schema, binding,
prediction, evidence, and support lineage.

The R2-only arm uses this same revised controller but has no Qwen objects,
probes attributed to Qwen, or Qwen-derived priors.

## Same-state counterfactual

Counterfactual evaluation occurs after the live episode and is never returned
to live cognition.

For every Qwen-altered control decision, up to eight, two fresh environments
replay the exact shared-arm prefix to the recorded pre-state digest. One branch
takes the actual Qwen-influenced action; the other takes the already recorded
no-Qwen fallback. The audit records the next-state level and the preregistered
residual in both branches.

If completion depends on a contiguous suffix of Qwen-influenced decisions, one
additional branch starts immediately before the suffix and runs the frozen
no-Qwen controller for the same remaining horizon. Every prefix, branch, and
suffix must replay exactly. A digest mismatch invalidates causal attribution.

## Binary verdict

The pair is `PASS` only when every validity gate holds and all of the following
are true:

1. `shared_live_qwen` completes level 1 within 48 actions.
2. `r2_only` does not complete within 48 actions, or the shared arm uses at
   least 25% fewer actions to the same level extent.
3. At least one prospective prediction receives exact environment evidence.
4. If any ambiguity or refutation occurred, Qwen produces an accepted
   evidence- or criticism-grounded non-alpha revision.
5. A revised Qwen schema becomes uniquely bound and prospectively confirmed.
6. That confirmed lineage changes at least one R2 control action relative to
   its recorded same-state fallback.
7. The decisive one-step or suffix counterfactual favors the Qwen-influenced
   branch.
8. Both factual trajectories and the decisive counterfactual replay exactly.

A valid run that misses any clause is `FAIL`. Shared completion without causal
attribution is recorded as `SOLVE_WITHOUT_CAUSAL_ATTRIBUTION` but remains a
binary failure. A valid prospective control chain without completion is
`CONTROL_CHAIN_NO_SOLVE` and also remains a binary failure.

`INVALID` is neither pass nor fail and cannot be repaired or rerun under the
same version.

## Hard validity gates

Any of the following makes the pair `INVALID`:

- unequal initial observation digests or a non-fresh workspace;
- any forbidden artifact, note, semantic prior, action token, or future event
  entering Qwen or R2 cognition;
- a basis event at or after its derived write, a prediction after its
  transition, or any other causal-order violation;
- prompt tokens plus the 2,048-token reserve exceeding 16,384;
- any due Qwen request timing out, failing transport, or failing strict
  compilation;
- a support mutation without a committed environment-evidence edge;
- stable-object identity reuse with different content;
- ledger/hash corruption, cross-workspace reference, or checkpoint mismatch;
- failure to exactly replay either factual arm or a required counterfactual.

Support-authority, stable-ID, ledger/hash, workspace-isolation, or leakage
failure cancels the pair immediately. Context and transport failures also yield
`INVALID`, with no semantic interpretation of missing Qwen output. Any rerun
requires a new versioned experiment and a new freeze.

## Stop rules

An arm stops at the first of:

- level 1 completion;
- 48 committed environment actions;
- no simple legal action;
- a hard integrity or leakage failure.

An exhausted Qwen budget or the two-call alpha/abstention stop disables further
Qwen calls but does not end environment execution. There is no outcome-based
restart, threshold adjustment, prompt edit, schema injection, or budget
extension.

## Checkpoints and audit record

Atomic progress is written after every environment action and immediately
before and after every Qwen call and environment action. Each checkpoint
records the ledger head, graph revision, action count, level count, controller
state digest, pending request ID, and environment cursor.

The durable audit retains:

- exact Qwen requests, responses, schemas, usage, latency, and compilation;
- every prediction, transition, evidence return, criticism, and revision;
- no-Qwen fallbacks and Qwen-influenced decisions;
- factual and counterfactual recordings and replay certificates;
- prompt occupancy, dependency closure, support-authority, stable-ID,
  workspace-isolation, and hash-chain checks.

After interruption, an arm resumes only from the last mutually consistent
ledger, graph, controller, and environment checkpoint. An uncertain or
partially committed action is reconstructed by exact replay before continuing.

## Safe reuse from v1

The following mechanisms may be reused after their integrity tests pass:

- `shared-attention-census-v1/ledger.py`: content-addressed blobs, immutable
  events, hash chain, atomic JSON, and cursors;
- `shared-attention-census-v1/epistemic_graph.py`: canonical objects and edges,
  reducer, dependency-closed frontier, environment-only support authority, and
  metrics;
- `shared-attention-census-v1/qwen_cognition.py`: generic action/game-blind
  prompt, strict response schema/compiler, sparse cuts, pinned causal units,
  token accounting, and leakage guards;
- `shared-attention-census-v1/experiment.py`: fresh environment opening,
  pending/committed transition protocol, live Qwen transport, exact replay,
  and recorded same-state no-Qwen fallback.

Before reuse, v1.4 must add regression coverage for the `ls20` stable-identity
collision, correct global hard-failure classification, add prediction and
evidence-return graph objects, enforce non-alpha revision, and implement exact
counterfactual branch replay. `census.py` may be reused only for descriptive
analysis; its buckets do not decide this binary experiment.

No v1 semantic object, Qwen reply, grounding, support, action sequence, or
controller state is reusable in the live v1.4 pair.
