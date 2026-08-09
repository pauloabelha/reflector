# Parallel Cognitive Workspace v1.3 — result

Verdict: **grounded pickup achieved; control gate failed**. Held-out games stay
paused.

## Durable outcome

- Both fresh arms committed 25 actions with the identical sequence
  `[1,2,3,4,5,7]` repeated four times, then `1`.
- Both ended level 0 at digest
  `75728952833d5ca5ebc60e6bf6003b381d2d6c8f1e516aea73e1699b2c3d22eb`.
- The R2-only arm completed fresh replay verification.
- The shared arm also completed its fresh replay before final result assembly;
  result assembly then raised `KeyError: 'objects'` because one metric still
  expected the pre-columnar initial materialization format. All 25 transitions
  and graph events remain durable.

## Cognitive chronology

1. Turn 1 proposed
   `SameOutline(a,b) -> Decrease TranslationAlignmentResidual(a,b)`.
   Its situated explanation was condition-false. R2 returned an exact,
   untruncated witness with six oriented substitutions and three effect pairs.
2. Turn 2 received that witness but repeated the same schema alpha-equivalently.
   This is a model decision failure, not context or DSL loss.
3. Turn 3 proposed
   `AlignedHorizontal(a,b) AND DifferentInteriorLayout(a,b) -> Decrease TranslationAlignmentResidual(a,b)`.
   R2 uniquely grounded the unordered effect pair `f00/f01`, committed one live
   binding, and wrote one `grounds_pickup` edge from Qwen to R2.

The selected pair is probably semantically wrong: `f00/f01` are horizontally
aligned and have different interior layouts, while the likely task pair
`f01/f02` shares its interior layout. Qwen optimized uniqueness without
establishing task relevance.

The action-25 decision remained fallback action 1 with `prior_used=false` and
no changed action. The new binding had zero local confirmations and no learned
action delta. Therefore the full proposal→grounding→control→environment chain
did not complete, and ar25 was not solved.

## Protocol findings

- The 4,000-unit context budget worked: the full ambiguity unit reached Qwen.
- The third task was queued immediately after turn-2 integration, before R2
  evaluated that repetition. It could see the older criticism but not the exact
  repeated derivation or a new criticism. This violates the intended
  proposal→grounding→criticism→revision order.
- Compact delta grouping hid the exact newest Qwen derivation. Live causal
  derivation/target/criticism units must be pinned losslessly.
- A gate that requires local confirmation before prior control must leave more
  than one transition after late binding. The 25-action budget could not by
  itself demonstrate a confirmed later override.
- Roughly 9,900 graph objects / 9,600 outer events by action 25 made the paired
  gate take about 58 minutes. Transactional batch events or snapshot-delta
  objects are required before any whole-corpus census.

No v1.4 live gate is authorized by this result. First repair reporting,
turn-order causality, exact live-derivation pinning, and event-volume scaling;
then preregister a budget that permits confirmation followed by influence.

