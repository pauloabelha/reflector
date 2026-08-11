# Parallel Cognitive Workspace v1.9

## Frozen question

Can a fresh, generic shared-cognition controller solve public `ar25` level 1
because a live Qwen proposal is prospectively tested, returned to Qwen as exact
environment evidence, revised non-trivially, confirmed, and then used by R2
control?

This is one binary paired experiment, not a prompt-tuning loop or a census.
There are exactly two arms:

- `r2_only`
- `shared_live_qwen`

Both arms use the same v1.9 R2 controller and independent fresh environments.
The shared arm's only additional input is Qwen output generated live inside
that arm. No proposal, schema, explanation, note, trace, cognitive object, or
controller state from an earlier run is allowed.

## Why v1.9 exists

v1.8 removed v1.7's serving-context failure by using a 24,576-token Qwen
context, and all four calls transported and compiled. It nevertheless ended in
a valid failure: prospective evidence for a live proposal was durable in the
graph, but a uniquely grounded proposal did not create the explicit
criticism/revision task needed to return that evidence to Qwen as a semantic
obligation.

v1.9 freezes three generic reachability corrections before any new live run:

1. Every qualifying prospective evidence return creates one exact,
   dependency-linked criticism/revision packet, whether the current grounding
   is ambiguous, supported, or refuted.
2. The original five-probe intention is enforced by type: no more than four
   ambiguous-population probes, plus one probe reserved exclusively for
   confirming a later unique non-alpha revision. The reserved probe cannot be
   consumed by the initial ambiguity.
3. The environment-action budget is 64 per arm. With calls sourced at actions
   `0, 12, 24, 36` and integrated eight actions later, a final revision at
   action 44 still has one confirmation action and 19 possible control actions.

The context window remains v1.8's 24,576 tokens. The generic prompt,
vocabulary, strict response compiler, environment-only support authority,
frontier, Qwen model and sampling parameters, call schedule, and original
strict binary gate remain unchanged except where this document explicitly
states otherwise.

## Frozen execution

The environment revision, code, config, prompt, response schema, reducer,
model file and hash, quantization, server parameters, and seed must be frozen
before either environment is reset. Both arms must begin from the same initial
observation digest and empty external cognition. Neither arm may inspect the
other while running.

Each arm has one environment worker, with at most two ARC workers total. The
pair may run concurrently. Qwen transport is serialized and belongs only to
the shared arm.

- Environment-action budget: 64 per arm.
- Level target: first completion of level 1.
- Qwen-call budget: four.
- Eligible source boundaries: actions `0, 12, 24, 36`.
- Deterministic integration: exactly eight logical actions after each source,
  at actions `8, 20, 32, 44` if the arm has not already terminated.
- Context window: 24,576 tokens, including a hard 2,048-token completion
  reserve.
- Maximum completion: 2,048 tokens, including at most 1,024 thinking tokens.
- Per-call timeout: 180 seconds.
- Probe budget: at most four ambiguous-population probes and at most one
  unique-revision confirmation probe; at most five total.
- Qwen-influenced control budget: at most 24 decisions.
- Counterfactual audit: the first eight changed control decisions plus at most
  one contiguous influenced suffix.

The single `generic_prospective` frontier remains fixed at 24 roots and 6,400
frontier units. It is a generic dependency-closure budget, not an
`ar25`-specific salience rule. A required exact causal packet that cannot fit
the frozen context makes the pair `INVALID`; it is never silently truncated.

## Isolation and leakage boundary

The shared workspace begins with no externally authored cognitive object. A
Qwen request may contain only the generic prompt and a projection of the live
epistemic graph built during that fresh episode. The game identifier is
transport metadata and is omitted from Qwen content. Environment actions are
represented only by opaque intervention IDs. Action names, action numbers,
policies, rewards, solutions, and game tokens are forbidden in requests and
responses.

The following are prohibited live inputs:

- frozen or replayed Qwen proposals;
- external schemas or explanations;
- user notes, including ARC or `ar25` notes;
- known solutions, action traces, rewards, or future recording outcomes;
- another game's cognitive objects;
- any prior run's semantic objects, graph state, controller state, response,
  grounding, support, or action preference.

Earlier artifacts may be used before freeze only as read-only codec, replay,
token-capacity, and integrity-test fixtures. They may not seed or select any
semantic content in the live pair.

## Prospective cognition loop

### 1. Live proposal and R2 grounding

Qwen may write only variable-based schemas, situated explanations over visible
stable IDs, attention contributions, or expansion requests. It may not choose
or describe an environment action and may not assert empirical support.

R2 grounds each accepted schema against the current live graph. Competing
groundings remain distinct. An ambiguous or incomplete grounding cannot enter
control, and its complete bounded witness is committed as structured
criticism.

### 2. Prediction before intervention

R2 may choose a probe using only its frozen generic prospective controller.
Before execution it commits immutable one-action predictions containing:

- the pre-state observation digest and basis revision;
- schema, derivation, binding, and effect-pair IDs;
- an opaque intervention ID;
- current and predicted residuals and direction of change;
- horizon, expiry, and candidate identity.

A prediction written at or after its transition is invalid. Probe actions are
exploration and never count as improved control.

At most four probes may be selected while the active population is ambiguous.
The fifth and final probe slot is unavailable to such a population.

### 3. Exact prospective evidence-return packet

After an intervention, the environment commits the transition, observed
residual, and adjudication. Only the environment reducer may emit support,
refutation, unresolved, or expiry judgments or mutate empirical support. A
direct `supports` or `refutes` judgment is qualifying evidence for the v1.9
revision packet; an unresolved or expired prediction cannot satisfy the
evidence or confirmation gate.

At each eligible Qwen boundary with new qualifying evidence for an active Qwen
target, the reducer commits exactly one structured evidence-return criticism
and revision task covering all qualifying evidence through that boundary. This
applies to an ambiguous grounding and also to a uniquely grounded proposal:
successful evidence is feedback to be interpreted, not a reason to omit the
Qwen half of the loop. The request basis is recorded only after this criticism
has been committed, so the task can never cite a future object.

The next eligible Qwen request pins one exact causal packet:

`Qwen derivation -> schema -> grounding/criticism -> prospective prediction -> transition -> environment evidence`

The packet contains, with stable IDs and created revisions:

- the semantic target, its alpha signature, and revision lineage;
- the complete bounded grounding population, effect pairs, candidate
  substitutions, and distinguishing visible relations;
- every qualifying prediction and environment-evidence judgment after the
  criticism and no later than the request basis;
- pre-state digest, opaque intervention, predicted residual/delta, observed
  residual/delta, verdict, transition ID, and evidence ID;
- exact dependency links needed to audit causal order and support authority.

The packet may use a canonical columnar representation, but its documented
fields are exact. Unexecuted prediction alternatives and unrelated graph churn
need not be copied into the packet; their exact objects remain addressable in
the authoritative ledger. Required evidence rows may not be summarized,
sampled, substituted by support counts, or dropped to meet a token budget.
Future evidence is forbidden.

The request validator independently recomputes qualifying evidence from the
graph. The packet's IDs and row count must match that set exactly. A mismatch,
missing dependency, causal-order violation, or lossy replacement is
`INVALID`.

### 4. Evidence-citing non-alpha revision

An evidence-return criticism activates the existing revision rule. Qwen must
either:

- emit a schema revision tied to the exact target and cite visible criticism
  or evidence IDs;
- request expansion of visible stable IDs; or
- abstain.

A counted revision must change canonical relational conditions or consequence.
Variable renaming, argument reversal for a symmetric predicate, conjunction
reordering, explanatory paraphrase, or resubmission of the target alpha
signature is rejected. Qwen-created objects begin at empirical support zero.

Two consecutive valid abstentions or rejected alpha repeats disable later
Qwen calls. R2 then continues to the ordinary arm stop. A transport or strict
compilation failure is not an abstention; it is `INVALID`.

### 5. Reserved confirmation and revised R2 control

A revised Qwen schema may affect control only when its grounding is complete
and selects exactly one effect pair. That revision may use the one reserved
confirmation probe. The probe prediction must be committed prospectively and
receive environment evidence before the revision becomes control eligible.

The reserved confirmation cannot be borrowed by an ambiguous schema and
cannot be replenished. A failed or unresolved confirmation therefore leaves
the revision ineligible for control in this run.

At every state R2 first records the action its frozen same-state no-Qwen
controller would choose. Only a uniquely grounded, prospectively confirmed
non-alpha revision may change the subsequent decision from probe to control.
The changed control decision must cite the complete schema, binding,
prediction, evidence, and support lineage.

The R2-only arm uses the identical v1.9 controller and budgets but has no Qwen
objects, Qwen-attributed probes, or external priors.

## Same-state counterfactual

Counterfactual evaluation occurs only after the factual episode and is never
fed back into live cognition.

For every Qwen-altered control decision, up to eight, two fresh environments
replay the exact shared prefix to the recorded pre-state digest. One branch
takes the factual revised-control action; the other takes the already recorded
same-state no-Qwen fallback. The audit records next-state level and the frozen
target residual in both branches.

If completion depends on a contiguous suffix of Qwen-influenced control, one
additional branch begins immediately before that suffix and runs the frozen
no-Qwen controller for the same remaining horizon. Every prefix, branch, and
suffix must replay exactly. Probe differences do not qualify as changed
control and do not create causal-credit branches.

## Binary verdict

The pair is `PASS` only when every validity gate holds and all of the following
are true:

1. `shared_live_qwen` completes level 1 within 64 committed actions.
2. `r2_only` does not complete within 64 actions, or the shared arm uses at
   least 25% fewer actions to the same level extent.
3. At least one prediction committed before its intervention receives exact
   environment evidence.
4. A later Qwen request receives the exact prospective evidence-return packet,
   and Qwen produces an accepted evidence-citing non-alpha revision of its
   exact semantic target.
5. That revision becomes completely and uniquely grounded and receives the
   reserved prospective confirmation.
6. The confirmed revised lineage changes at least one R2 control action from
   its recorded same-state fallback.
7. The decisive one-step or suffix counterfactual favors the factual
   Qwen-influenced branch.
8. Both factual trajectories and every required counterfactual replay exactly.

A valid run missing any clause is `FAIL`. Shared completion without the full
causal chain is recorded as `SOLVE_WITHOUT_CAUSAL_ATTRIBUTION`; a complete
prospective control chain without level completion is
`CONTROL_CHAIN_NO_SOLVE`. Both remain binary failures.

`INVALID` is neither pass nor fail and cannot be repaired or rerun under the
same version.

## Hard validity gates

Any of the following makes the pair `INVALID`:

- unequal initial observation digests or a non-fresh workspace;
- any prohibited artifact, note, semantic prior, action token, game token, or
  future event entering live cognition;
- environment/model/config/prompt/compiler drift after freeze;
- a derived write at or before its basis, a prediction at or after its
  transition, future evidence in a request, or another causal-order violation;
- a missing, extra, truncated, non-exact, or causally disconnected required
  evidence-return packet row;
- prompt tokens plus the 2,048-token reserve exceeding 24,576;
- any due request timing out, failing transport, or failing strict
  compilation;
- a support mutation without committed environment evidence;
- stable-object identity reuse with different content;
- ledger/hash corruption, cross-workspace reference, or checkpoint mismatch;
- failure to replay either factual arm or a required counterfactual exactly;
- failure to enforce the typed four-plus-one probe partition.

Leakage, support-authority, stable-ID, ledger/hash, isolation, or frozen-config
failure cancels the pair immediately. Context and transport failures also
produce `INVALID`, with no semantic interpretation of absent output. Any rerun
requires a new version and a new freeze.

## Stop rules

An arm stops at the first of:

- level 1 completion;
- 64 committed environment actions;
- no simple legal action;
- a hard integrity, leakage, context, or causal-order failure.

The two-call alpha/abstention stop or exhausted Qwen budget disables further
Qwen calls but does not end factual environment execution. A call boundary
after factual termination is not due. There is no outcome-based restart,
threshold adjustment, prompt edit, schema injection, or budget extension.

## Checkpoints and audit record

Atomic progress is written after every environment action and immediately
before and after every Qwen call and environment action. Each checkpoint
records the ledger head, graph revision, action count, level count, controller
state digest, typed probe counts, pending request ID, and environment cursor.

The durable audit retains:

- exact Qwen requests, responses, schemas, usage, latency, and compilation;
- every grounding population, criticism, prediction, transition, evidence
  return, exact revision packet, and revision;
- ambiguous and reserved-confirmation probe counters;
- no-Qwen fallbacks and Qwen-influenced control decisions;
- factual and counterfactual recordings and replay certificates;
- packet-coverage, context, dependency-closure, support-authority, stable-ID,
  workspace-isolation, and hash-chain checks.

After interruption, an arm resumes only from the last mutually consistent
ledger, graph, controller, and environment checkpoint. A pending or uncertain
action is reconstructed by exact replay before continuation.

## Preflight and safe reuse

No environment may be opened until all v1.9 code and tests exist, the effective
config and manifest are frozen, and the server reports the exact frozen model
and `n_ctx=24576`.

Read-only v1.8 artifacts may be used to test serialization, causal ancestry,
packet completeness, token capacity, and replay. Preflight must demonstrate
that the evidence sets at each historical boundary are reproduced exactly and
that the complete rendered requests fit prompt plus reserve. Those artifacts
must never be loaded into the live v1.9 workspace or used to select a schema,
predicate, entity, action, threshold, or salience weight.

Ledger, graph, transport, strict compiler, checkpoint, and replay machinery may
be reused only after their integrity tests pass. No earlier semantic object,
Qwen response, grounding, support, trace, or controller state is reusable in
the live pair.
