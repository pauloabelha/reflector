# Parallel Cognitive Workspace v1 — balanced census results

Date: 2026-08-09  
Branch: `shared-attention-census-v1`  
Frozen run: `balanced`, 25 public ARC games, fresh paired `r2_only` and
`shared_attention_qwen` arms, 32-action cap, Qwen turns at actions 0/8/16,
four ARC workers, one resident Qwen FIFO.

## Verdict

**The shared cognitive substrate is mechanically real, but this controller is
not control-promising yet.**

The run produced no first-level completion in either arm, no paired task gain,
and no action saving. Qwen-derived objects crossed into R2 and grounded in
multiple real games, but there was no grounded R2-to-Qwen return pickup and only
`ar25` reached evidence-backed action influence. Those four changed `ar25`
actions reduced the selected relational residual but pursued the wrong proxy and
did not advance the level.

This is therefore not evidence for Kaggle > 1. It is evidence that the proposed
workspace can carry a Qwen hypothesis through salience, R2 grounding, local
confirmation, and action arbitration without granting Qwen epistemic authority.

## Run completion and validity

- All 50 jobs reached terminal durable artifacts in about 3 hours 14 minutes.
- 41 episodes completed normally; 9 recorded typed failures.
- 17 games have both completed arms. All 34 of those completed episodes replay
  exactly, every pair has the same initial digest, and paired trajectories can be
  compared directly.
- Six completed pairs were zero-action complex-action abstentions: `ft09`,
  `lp85`, `r11l`, `s5i5`, `tn36`, and `vc33`.
- Eleven completed pairs executed 32 actions in each arm. Every one remained at
  level 0. No actionful pair showed a level gain, action saving, or hard level
  regression.
- Thirteen completed pairs satisfy replay, same-start, and context gates. Ten of
  those also have complete Qwen transport; only four strict-valid pairs are
  actionful: `ar25`, `cn04`, `ka59`, and `m0r0`.
- No completed result reports a support-authority violation.

The 9 typed episode failures were:

- Mandatory exact frontier larger than the frozen 4,800-unit budget in six
  shared arms: `bp35` (6,312), `dc22` (6,524), `re86` (6,537), `sb26` (5,551),
  `su15` (5,183), and `tr87` (5,580). These are context-feasibility invalids,
  not model losses.
- `ls20/shared_attention_qwen`: stable epistemic object identity was reused with
  different content. This is a graph-integrity failure.
- Both `sp80` arms: the harness could not normalize an observation with no
  rectangular frame. This is a symmetric harness invalid. Exact ledger audit
  showed that action 25 had already produced a valid 64x64 `GAME_OVER`
  observation; the harness incorrectly attempted action 26, and ARC returned
  terminal metadata with `frame=[]`.

Four otherwise completed actionful shared arms exceeded the conservative
16,384-token context admission gate after reserving 2,048 completion tokens:
`cd82` (+344), `g50t` (+42), `sc25` (+449), and `wa30` (+874). They remain useful
diagnostics but are excluded from strict evidence. `lf52`, `sk48`, and `tu93`
fit context but each suffered one transport error, leaving two valid
compilations out of three.

Post-run inspection found that `admit_request_context()` was tested but never
wired into the production request path; server-reported usage was the first
actual occupancy check. The available llama.cpp count/tokenize endpoints do not
run the same multimodal image-token path as completion, so a heuristic local
counter would not repair this honestly. Before v1.4, the server needs an exact
multimodal dry-run count endpoint, and the FIFO must reject overflow immediately
before posting the byte-identical completion request.

## Mechanistic results

Across the seven context-valid, replay-valid actionful pairs, six shared arms
recorded a grounded Qwen-to-R2 pickup: `ar25`, `ka59`, `lf52`, `m0r0`, `sk48`,
and `tu93`. Including context-invalid diagnostic runs, `cd82` and `wa30` bring
the observed total to eight. Grounded R2-to-Qwen pickup was zero everywhere;
R2-to-Qwen *exposure* events are visibility records and must not be counted as
grounded reuse.

Only `ar25` crossed from grounding into control:

1. Qwen proposed a relational potential.
2. R2 uniquely grounded it and recorded a Qwen-to-R2 pickup.
3. Environment transitions supplied four support edges.
4. Four later decisions used the confirmed prior and differed from the paired
   fallback action.
5. The selected pair's residual fell from 92 to 44.

The level nevertheless remained unsolved after 32 actions. Inspection shows the
binding selected the wrong pair for the intended ar25 concept, so this is a real
causal control path but not a useful task-level explanation.

All other grounded proposals were inert: no directly learned action delta, no
support, no prior use, and no action divergence. In `m0r0`, for example, a
proposal became uniquely bindable as the scene changed and then had sixteen
later actions in which to learn, yet still produced no confirmation or control.

`wa30` is the clearest criticism-driven semantic revision: Qwen changed
`SameOutline -> Decrease(TranslationAlignmentResidual)` into
`SameOutline AND AlignedVertical -> Decrease(TranslationAlignmentResidual)`,
which isolated one effect pair. It still produced no support or action change,
and its context and transport gates failed, so it is diagnostic rather than
counted positive evidence.

For the 17 completed shared episodes, the durable result summaries contain 33
Qwen calls, 29 valid compilations, 361,363 total tokens, and 977.7 seconds of
server latency. Failed shared arms contain additional durable calls, so those
figures are a lower bound on total inference work. On the 17 completed pairs,
shared execution consumed 15,621 seconds of summed episode time versus 12,660
seconds for control, an aggregate overhead of 2,961 seconds while running in
parallel.

## What v1 established

The experiment validates several architectural claims independently of score:

- R2 and Qwen operated over one event-sourced epistemic graph rather than two
  authoritative private states.
- Qwen received current images, recent and selected historical transitions, a
  dependency-closed epistemic cut, and ordered deltas from a durable cursor.
- Situated Qwen claims terminated in visible entity/frame addresses or explicit
  open ports; R2, not Qwen, adjudicated grounding.
- Qwen and R2 could raise attention, while only environment-authored evidence
  changed support.
- Self-built R2 objects, Qwen-derived objects, derivations, criticism, attention,
  evidence, and action provenance remained distinct.
- Action and epistemic events were checkpointed and replayable; graph batches
  reduced persistence overhead without changing the recovered event stream.

What v1 did **not** establish is the stronger shared-cognition claim. We observed
no grounded bidirectional chain and no successful level control. Qwen often
collapsed into a generic `DifferentOutline` or `SameOutline` plus translation
alignment hypothesis, then alpha-repeated it despite exact ambiguity witnesses.
Unique grounding was often merely uniqueness, not correct task-role selection.

## Preregistration deviation

The `ls20` stable-ID integrity error should have requested global cancellation
under the frozen rules. The runner misclassified its exact wording as a job-local
failure, so the scheduler continued. Workspaces remained isolated and all later
artifacts are mechanically usable, but results from `m0r0` onward are labeled
post-deviation exploratory rather than an untouched preregistered census. The
classifier has now been corrected with a regression test; that fix was made only
after this run and did not alter any result.

The post-run harness now gates `WIN` and `GAME_OVER` before frame parsing,
Qwen integration, decision-making, or `ActionPending`, and reuses the exact last
committed terminal digest. Recovery of a *pre-existing* pending action whose
predecessor is already terminal still needs an explicit abandonment event in a
future ledger protocol revision.

## Recommended next experiment

Do not repeat the 25-game census yet. Run a small, newly frozen v1.4 gate after
four generic repairs:

1. Make changing binding state versioned rather than reusing a stable semantic
   identity; invalidate superseded binding snapshots explicitly.
2. Replace the fixed 4,800 frontier ceiling with mandatory-first exact packing,
   addressable lossless pages, and exact admission before every call. A frozen
   profile must be feasible corpus-wide or emit a typed infeasibility without
   masquerading as a cognitive result. Exact admission requires a server-side
   multimodal dry-run counter; the current text-only token endpoints are not
   sufficient.
3. After a Qwen proposal uniquely grounds, make R2 schedule a bounded
   discriminating calibration intervention. A binding should not sit inert for
   sixteen actions while the fallback cycle continues.
4. Record explicit grounded R2-to-Qwen reuse when Qwen revises because of an R2
   criticism/evidence object; exposure alone is insufficient.

The v1.4 development set should be only `ar25`, `wa30`, and one negative control
such as `cn04`, with fresh paired arms and no injected frozen proposal. Release
to new held-out games only if live shared cognition completes ar25 level 1,
produces at least one prospective grounded bidirectional chain, and replays
exactly. The intended ar25 target remains the earlier 17-action behavior; merely
reducing an arbitrary relational residual is not a pass.

## Durable artifacts

- `artifacts/SUMMARY.json`: 41 completed results and 9 typed failures.
  SHA-256 `f0f821653ea171d0626a5594059c3e8109e51135c890cd2aef1b13ca6bb5a11b`.
- `artifacts/PARTIAL_RESULTS.json`: terminal aggregate and run bookkeeping.
  SHA-256 `032fc93ed03635a09be2db03a8818124d5e4abaf48dee5bca03ecf8c2c6ac5dd`.
- `artifacts/progress/`: per-job human-readable terminal checkpoints.
- `artifacts/workspaces/`: hash-chained action, cognition, graph, request, and
  response ledgers used for the mechanistic audits.
- `STATUS.md`: chronological job completion/failure record.
