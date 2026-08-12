# R2 glue cumulative report

This report is append-only by checkpoint. Claims use the repository status
convention: **implemented**, **observed**, **inferred**, or **prospective**.

## Checkpoint 000

**Implemented:** the current R2.2/R2.3/CAE architecture is merged and pushed on
`main`; branch `glue` begins from that exact commit.

**Observed:** the focused 123-test suite passes. The inspected live AR25 snapshot
contains correct CAE support/refutation transitions but no grounded planner
route.

**Inferred:** the closed semantic schema is a material integration bottleneck.
It lets Qwen name a prior verb but not express and operationalize the structural
abduction motivating that verb.

**Prospective:** a bounded generic measurement-proposal protocol will improve
semantic-to-control pickup across games. This remains unproven until live and
cross-case evidence exists.

## Checkpoint 001

**Implemented:** verbs and built-in observables remain available as priors, but
neither prompt nor controller imposes a verb-specific observable/direction
mapping. Qwen may propose one named residual through
`r2-spatial-set-residual-v0`, selecting actor/target spatial-set features,
comparison, coordinate frame, and optional scene separation. R2 validates the
closed expression, rejects custom observables without definitions and name
collisions, and evaluates accepted proposals through ordinary grounding,
simulation, planning, and settlement paths. The measurement fingerprint is part
of control identity.

**Observed:** 135 focused tests pass. The full 234-test suite has 233 passes and
one failure because `experiments/parallel-cognitive-workspace-v1-16/artifacts/
SUMMARY.json` is absent on the unmodified `main` baseline. No new functional
failure was observed.

**Inferred:** the protocol can represent occupancy-to-negative-space matching
without encoding that this relation means FIT, without naming a game, and
without granting Qwen authority. Synthetic evidence shows a scene gradient, an
exact zero terminal, and fail-open behavior when the selected feature is empty.

**Prospective:** Qwen will select a useful measurement in live play, R2 will
ground the intended roles among distractors, and this will improve an action.
None of those claims is established yet.

## Checkpoint 002

**Implemented:** semantic proposals now have a direct grammar-visible split
between built-in and proposed measurements plus dependent compiler checks.
Malformed siblings are quarantined without losing a valid frame-zero
explanation. CAE geometry is summarized before the semantic context budget so
rejection diagnostics survive truncation. Proposal identity includes
compiler-owned defaults, and an unchanged failed proposal is retired after new
evidence while independent scratchpad/alias updates survive.

**Observed:** fresh AR25 runs reproduced malformed model output, the initial
whole-response liveness failure, a valid-but-ungroundable custom measurement,
and stale repetition. After repair, frame zero remained live, the bad candidate
had no control authority, CAE promoted a seven-member motion group to SUPPORTED
after opposite vertical probes, rejection feedback remained visible, and the
repeated failed goal was cleared while play continued. The focused suite has
143 passing tests.

**Inferred:** the principal defect at this checkpoint was not missing domain
knowledge. It was loss of typed dependency and failure information across
generation, compilation, storage normalization, and bounded projection.

**Prospective:** preserving this boundary should improve robustness on other
games, but useful semantic-to-control pickup and score improvement remain
unproven. Checkpoint 003 must use a case selected independently of AR25's
negative-space affordance.

## Checkpoint 003

**Implemented:** no new production mechanism was added. The existing checkpoint
002 architecture was tested unchanged on `bp35`, selected by a predeclared
lexical rule rather than expected compatibility.

**Observed:** malformed frame-zero semantics were quarantined without halting.
After one changed transition, Qwen supplied a valid custom boundary residual;
R2 grounded it, authorized a discriminating probe, settled both role identities
as UNIQUE, observed stationary effects and zero potential progress, and kept
the planner at NO_PLAN. CAE generated no unsupported higher-order factor. A
later coordinate action carried a complete observed-region payload and effect
scope. The grounded role frontier contained 195 Pareto-equal candidates.

**Inferred:** the repaired semantic boundary transfers as a safety and liveness
property. It can also affect action selection through a genuinely grounded
probe. It has not demonstrated efficient ambiguity collapse, progress control,
level completion, or score gain.

**Prospective:** action-conditioned settlement may reduce the equivalent-role
frontier enough to yield a supported effect and useful control. Checkpoint 004
must measure that rather than infer it from a single successful probe.

## Checkpoint 004

**Implemented:** mechanism confirmation and positive goal-progress
confirmation are now distinct evidence channels. Repeated uniquely grounded
nonprogress can request semantic goal revision without deleting the learned
action effect. Settlement projections read fresh observer counters, removing a
one-decision feedback lag. A supported competing explanation suppresses
note-wide retirement.

**Observed:** the targeted semantic/planner/Qwen suite has 43 passes. The full
suite has 239 passes and the unchanged missing historical `SUMMARY.json`
failure. In fresh BP35 play, Qwen again proposed a generic alignment objective,
R2 grounded it as probe-only, and the first attempted settlement broke identity;
it correctly contributed no nonprogress evidence. With no intervening code
change, CD82 grounded a custom boundary residual as probe-only. Its same
grounded candidate accumulated zero-progress observations 1, 2, and 3 in the
immediately published semantic projection. Qwen revised the proposal set from
outline compatibility to a distinct interior-compatible alternative; after
that alternative also lacked support, the goal list retired to empty by turn 7.

**Inferred:** the earlier bp35 failure was not only a weak semantic proposal.
R2 conflated evidence for an action mechanism with evidence for the usefulness
of the goal and projected settlement counters from a stale candidate snapshot.

**Observed architectural boundary:** repeated grounded zero progress now causes
semantic revision and eventual retirement without converting a stationary
mechanism observation into goal support. The trace does not demonstrate useful
control or completion.

**Prospective:** checkpoint 005 will test whether the remaining inefficiency is
explained by observationally equivalent role hypotheses and latent interaction
context across command sequences. Neither representation may contain game or
action-token semantics.

## Checkpoint 005

**Implemented:** each semantic turn now carries one exact `model_scratchpad`
instead of duplicating the same durable note inside `prior_working_note` and
again as `scratchpad_context.qwen_note`. The compact prior projection retains
goal proposals, action aliases and their evidence, open questions, citations,
transition basis, and consolidation state. Compile-time alias evidence accepts
the new canonical location and legacy duplicated replays.

**Observed:** the first CD82 trace crashed at turn 9 because the exact mandatory
request occupied 16,678 tokens in a 16,384-token window. Removing the nested
note reduced a subsequent overflow to 50 tokens, proving the source but not yet
restoring liveness. Removing the remaining scratchpad duplicate reduced a
representative action-10 request from the earlier 47,964-byte envelope to
44,812 bytes. In the exact rerun, Qwen call 10 was admitted, completed, action
10 settled, and call 11 began without context error. The focused suite has 86
passes; the full suite has 240 passes and the same missing historical artifact
failure.

**Inferred:** the crash was accumulated transport duplication, not an
insufficient model window or a need to discard causal evidence. Single-copy
projection restores bounded semantic-loop liveness while preserving the
authoritative ledger and all current settlement evidence.

**Prospective:** checkpoint 006 returns to sequence-conditioned mechanisms and
equivalent-role efficiency. No competence or score gain is claimed.

## Checkpoint 006

**Implemented:** atomic action effects no longer require a pre-existing Qwen
goal. Every transition attempts ordinary correspondence for unassigned
entities, but records an effect only when predecessor-to-successor and
successor-to-predecessor fits are both UNIQUE and select each other. Entities
already tracked by a goal remain owned by the stricter role settlement path.
Ambiguous duplicates, disappearance, broken identity, and deformation add no
rigid effect.

A later semantic goal with a supported exploration-learned mechanism but open
role identity is now eligible for an identity-discriminating probe. It cannot
receive progress authority until that probe settles required correspondences as
UNIQUE. Once settled, the ordinary one-step/planner gates consume the same
effect model.

**Observed:** CN04 was predeclared as the next lexical transfer game. Before an
active semantic explanation, action 2 produced mutually unique rigid effects,
including a 3-cell translation and invariant entities, while adjudication stayed
`untested-open-mechanism`. CAE independently retained a three-member coherent
motion candidate from the same transition. Synthetic integration verifies the
complete handoff: unguided effect learning, identity-only probe, UNIQUE
settlement, then positive progress/plan eligibility. The focused suite has 132
passes; the full suite has 244 passes and the unchanged missing historical
artifact failure.

**Inferred:** causal learning had been incorrectly downstream of semantic goal
selection. Separating mechanics acquisition from telic interpretation lets
exploration remain useful when Qwen abstains or is wrong, while preserving all
identity and authority gates.

**Prospective:** checkpoint 007 tests whether remaining contradictory effects
require observable state or predecessor-command context. Context will be added
only for repeated identical command scopes and entity types with genuinely
different mutually unique outcomes.

## Checkpoint 007

**Implemented:** unassigned rigid effects are now pooled by intrinsic entity
type within one environment intervention. Agreeing instances contribute one
model observation plus an `entity_count` audit field. If mutually unique rigid
instances of the same type have different deltas, R2 records no type-level
effect: the intrinsic type is proven insufficient, and invariant siblings
cannot outvote a moved instance. Goal-bound role effects remain separately
settled.

**Observed:** the first DC22 transition originally emitted 32 entity-level
effect records. On the exact rerun, pooling emitted 14 type-level records. One
invariant record represented 11 agreeing entities and another represented 8;
the genuine 2-cell translation remained separate. Synthetic tests verify that
two agreeing instances increment model support once and that heterogeneous
same-type outcomes add no model observation. The focused suite has 133 passes;
the full suite has 245 passes and the unchanged missing historical artifact
failure.

**Inferred:** multiple objects in one scene are correlated witnesses to one
intervention, not independent transition trials. Per-transition pooling avoids
pseudo-replication and turns within-type heterogeneity into an explicit demand
for a missing role or context factor.

**Prospective:** context induction remains warranted only after repeated
identical command scopes reproduce heterogeneous rigid outcomes with an
observable discriminator. The live DC22 semantic-admission failure below took
priority; context induction moved to checkpoint 009. No game-specific state or
action meaning is allowed.

## Checkpoint 008

**Observed:** on DC22, Qwen copied the frame-0 scratchpad after Actions 1–3,
including the assertion that there was no prior state, while separately citing
the new transition traces. Once R2 reported two uniquely grounded nonprogress
observations, the existing guard retired the repeated goal proposal but still
accepted the stale explanation. A first rejection also proved transient: after
the failed candidate disappeared, the next retry could admit the same semantic
state under a fresh evidence reference.

**Implemented:** an explicit R2 semantic failure plus new environment evidence
now starts a durable semantic-revision obligation. It survives rejected retries
and candidate retirement, and clears only after a valid five-field scratchpad
changes both its assessment (`notes`) and at least one explanatory field
(`explanation`, `goal`, or `expectation`). Stable hypotheses remain admissible
when no explicit failure exists. The obligation resets at episode and level
boundaries and contains no game, palette, geometry, action, or verb rule.

**Live evidence:** exact DC22 replay rejected call 4 with
`evidence-stale-semantic-state-repetition`. Later retries, including call 7,
remained rejected with `evidence-stale-semantic-revision-pending`; grounded R2
exploration continued. The focused suite has 135 passes; the full suite has 246
passes and the unchanged missing historical artifact failure. No DC22
completion or score gain is claimed.

**Prospective:** checkpoint 009 returns to context induction, but only if
repeated identical command scopes reproduce heterogeneous rigid outcomes with
an observable discriminator.

## Checkpoint 009

Heterogeneous mutually unique rigid outcomes now emit a bounded
`unresolved_effect_contexts` record. It preserves the command scope, intrinsic
region type, distinct deltas, and per-outcome entity counts, with explicit
`telemetry-only-no-effect-learning` authority. The effect model remains
unchanged. This distinguishes “no correspondence evidence” from “intrinsic
type was tested and proved insufficient” without prematurely inventing a role,
sequence state, or spatial context. A synthetic transition verifies one
invariant and one translated instance are reported while model support remains
empty. Context induction is not yet authorized; repeated cross-transition
evidence and an observable discriminator are still required.

A committed read-only ledger audit then replayed R2's exact component,
mutual-unique correspondence, rigidity, type-pooling, and command-scope logic
over 101 deduplicated recorded transitions spanning AR25, BP35, CD82, CN04, and
DC22. It found zero unresolved-context records and therefore zero repeated
signatures. Identical live reruns were deduplicated by game, predecessor digest,
successor digest, and action. The result contradicts any current claim that a
sequence or spatial context factor is empirically demanded. Checkpoint 009 is
complete with the telemetry retained and no context induced.

**Next observed bottleneck:** DC22 Qwen calls 4–8 received an explicit semantic
failure packet but repeated the same failed fit proposal and frame-0
scratchpad. The ordinary revision turn asks the small local model to regenerate
several unrelated products. Checkpoint 010 will test a focused repair transport
while preserving the canonical turn, exact causal images, compiler validation,
and R2-only grounding/control.

## Checkpoint 010

**Observed:** ordinary DC22 semantic turns carried about 30.8k prompt
characters and 8.6k model tokens while requiring Qwen to regenerate aliases,
citations, abductive composition, goal proposals, and the five-field scratchpad.
After explicit nonprogress, the small local model repeatedly copied the failed
state.

**Implemented:** explicit semantic failure now selects a focused repair
transport. It retains the canonical turn and exact causal images locally for
validation, but sends the prior scratchpad, latest transition/R2 settlement,
failure obligation, and bounded semantic projection with unrelated sparse-cut
and output products omitted. The response schema forces aliases, citations,
and abductive compositions empty for generation and allows goal-proposal
abstention. The compiler preserves already-settled evidence-cited aliases,
still quarantines repeated or malformed goal proposals, and admits a repair
only after `notes` plus one explanatory field change. A generic temporal
coherence gate also rejects any post-action scratchpad that asserts there is no
prior state/history while an exact transition evidence reference exists.

**Live evidence:** focused DC22 requests were 15.35–15.93k characters and
4,843–5,102 prompt tokens, versus 30.8k characters and 8,610 tokens for the
preceding ordinary turn (about 44% fewer prompt tokens). Two insufficient
repairs were rejected. The next repair acknowledged the prior alignment state
and latest displacement, was accepted as context, and had its repeated goal
proposal separately retired. `goal_proposals` became empty while the prior
evidence-cited action alias survived. The focused suite has 137 passes; the
full suite has 249 passes and the unchanged missing historical artifact
failure.

**Limit:** no DC22 completion or score improvement is claimed. Checkpoint 011
must test whether subsequent revised hypotheses reduce grounded nonprogress or
improve probe efficiency, including on another game.

## Checkpoint 011

**Observed:** an exact DC22 replay on the pushed checkpoint-010 build reached
six nonprogress observations while focused Qwen repairs remained rejected. The
durable failed alignment note was correctly retained for revision, but the same
goal still entered every subsequent action ranking. Semantic repair therefore
did not yet imply control repair. A cross-game CD82 run then exposed a separate
transport failure: its second post-action request occupied 16,884 tokens in a
16,384-token context. Shrinking the dependency-closed graph frontier could not
help because its mandatory closure was only 59 tokens; the fixed prompt and
causal visual transport dominated the request.

**Implemented:** a durable semantic-revision obligation now records the exact
canonical keys of the proposals whose grounded potential produced explicit
failure evidence. While the obligation is pending, the controller filters only
those proposals from action ranking. The note remains visible for audit and
Qwen revision, unrelated proposals remain eligible, and learned causal effects
are untouched. An accepted repair cannot silently reinsert an exact suspended
proposal; it is retired independently with an evidence-linked reason. The
suspension clears with the accepted revision or existing episode/level reset.

Ordinary post-action semantic updates now use a compact, generic instruction
surface rather than replaying the complete frame-zero architecture tutorial.
The strict response schema, prior five-field scratchpad, canonical turn,
dependency-closed evidence, ordered predecessor/successor images, compiler
checks, and R2-only action authority remain unchanged.

**Live evidence:** on fresh DC22, failure threshold was reached at turn 3.
While call 4 was in flight and again after call 5 was rejected, the durable
alignment proposal stayed visible but the R2 control projection had no active
explanation, zero controller explanations, and `execution_authorized=false`.
Action selection returned to the generic information role rather than adding
three more probes to the failed potential. On fresh CD82, the pre-repair second
call failed admission by 500 tokens. The repaired replay completed and
integrated that call and the following call, continued through turn 3, and had
no context error. Its post-action text transports were 27.5k and 22.1k
characters while retaining both causal images.

The focused suite has 146 passes. The full suite has 250 passes and the one
unchanged failure caused by the absent historical
`parallel-cognitive-workspace-v1-16/artifacts/SUMMARY.json`.

**Limit:** this verifies authority withdrawal and context liveness, not a level
completion, score increase, or general ARC competence. Checkpoint 012 must
measure environment progress and hypothesis utility across games.

## Checkpoint 012

**Observed:** CD82 completed six semantic calls but quarantined every structured
goal: Qwen generated repeated roles such as `actor,actor` or constraints over
undeclared repeated `occluder` arguments. A read-only audit found 51 such
dependent-role failures in recorded AR25, BP35, CD82, CN04, and DC22 runs (44
invalid constraint arguments and 7 duplicate role arrays). JSON Schema's
`uniqueItems` did not make these cross-field dependencies reliably generatable
for the local constrained backend.

**Implemented:** newly generated measurable goals now use one grammar-visible
binary interface: `roles=[actor,target]`,
`potential_roles=[actor,target]`, and constraint arguments use those same two
ports. This is not a verb or game mapping. Semantic role meaning remains in the
verb, schema name, goal family, and relation predicate; R2 still binds both
ports to situated entities. The compiler remains backward-compatible with
existing multi-role notes.

New visual categorical constraints also cannot use `required`. Sameness,
difference, outline, interior, area, and value are unverified compatibility
clues, so generation may mark them `suggested`, `anti-clue`, or `unknown`.
Legacy required constraints and consolidation applicability contracts remain
readable. This prevents a Qwen visual guess from becoming a universal verb
definition or hard control gate.

**Live evidence:** fresh CD82 produced two consecutive valid goals with
canonical ports and zero compiler rejections, then validly abstained after
nonprogress. On AR25, Qwen proposed a spatial-set residual comparing occupancy
with enclosed negative space. With `same_outline` downgraded from a hard gate
to a suggestion, R2 grounded the differently shaped pair. The residual fell
from 53 to 32 over six environment-confirmed progress observations. Control
advanced from `PROBE_ELIGIBLE` to `PLAN_ELIGIBLE`; selected actions were backed
by causal-factorization plans rather than the verb label.

The focused suite has 147 passes. The full suite has 251 passes and one
unchanged missing historical artifact failure.

**Limit:** no AR25 level or score terminal has yet been observed. The semantic
model still named the hole-based residual `align`; the measurement, grounding,
settlement, and control path—not lexical fluency—produced the observed local
progress. Checkpoint 013 keeps the live run open until an environment terminal
or a new evidenced bottleneck appears.

## Checkpoint 013

**Observed:** near residual 27, AR25 probing changed visible role structure.
The semantic proposal remained byte-identical, but `control_goal_key` changed
twice because it included the defeasible role candidate's structural ID.
Progress confirmations reset from seven to zero and both role trajectories
were discarded. The apparent jump to residual 7 was therefore a different
grounding, not continuous progress of the tracked filler/receptacle pair.

**Implemented:** semantic goal identity now contains only the semantic control
objective: verb, observable, direction, formal potential ports, and role
constraints. The frame-local candidate ID remains in the grounding hypothesis
and ranking beam, but no longer namespaces goal evidence or trajectories. Once
an intervention selects one candidate, environment settlement creates role
trajectories under the semantic goal; later candidates are evaluated against
that persistent identity through translation, overlap, occlusion, and visible
structural change.

**Live evidence:** an exact fresh AR25 replay reproduced the prior sequence.
At the old reset point, a probe regressed the tracked residual from 27 to 30.
The repaired build retained the same semantic goal key, the same actor and
target trajectory IDs, and all seven progress confirmations. It then selected
a causal-factorized action and recorded an eighth confirmation. By turn 19 it
truthfully remained on the same pair at residual 30 and resumed discriminating
probes; it did not claim the prior spurious residual-7 jump.

The focused suite has 148 passes. The full suite has 252 passes and the one
unchanged missing historical artifact failure.

**Limit:** role continuity is repaired, but AR25 has not reached a local-zero,
level, or score terminal. Checkpoint 014 must discover a further control factor
or report the remaining plateau without changing goal identity.

## Checkpoint 014

**Observed:** the supported AR25 goal oscillated between residuals 27 and 30.
Lifetime confirmations correctly prevented false failure retirement, but a
consecutive-nonprogress counter was reset by every 30 → 27 recovery. Positive
local movement therefore concealed the absence of a new best frontier.

**Implemented:** R2 now tracks the best observed potential per semantic goal
and steps since that best improved. Four no-new-best steps on a goal with prior
progress request a focused complementary semantic hypothesis without
suspending the goal. The compiler preserves the canonical supported proposal
and appends only valid distinct alternatives. Accepted repair acknowledges one
goal/frontier epoch; rejected repair remains durable, while a later new best
permits a new plateau epoch.

**Live evidence:** exact fresh AR25 reached best 27 with seven confirmations,
then accumulated four no-new-best steps across the 27/30 oscillation. A locally
positive 30 → 27 return produced confirmation eight but did not reset frontier
stagnation. The focused action-17 request carried both plateau markers, kept the
same goal control-eligible, and retained it when Qwen abstained from a second
structured goal. The action-18 request carried neither plateau marker, proving
the accepted epoch was not redundantly repaired. The focused suite has 111
passes; the full suite has 254 passes and the unchanged missing historical
artifact failure.

**Limit:** no AR25 environment terminal or score improvement is claimed.
Checkpoint 015 uses other games to try to falsify this generic lifecycle.
