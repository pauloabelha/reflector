# `ar25` break-in analysis

## Outcome

The corrected live run completed level 1 in 38 actions. Factual replay and all
eight selected counterfactual branches replayed exactly. There were zero
support-authority violations.

The 38 decisions divide cleanly into:

- 20 fallback exploration decisions;
- 5 information-seeking probes;
- 13 goal-progress control decisions.

The persisted decision roles were 24 information, 1 progress-and-information,
and 13 goal-progress. Every cycle committed exactly one primitive and settled
it from the successor observation.

## Where the agent broke in

The action sequence was:

```text
1 2 3 4 5 7 1 2
1 1 1 1
3 4 5 7 2 3 4 5 7 2 3 4
2
2 2 2 2 2 2 2 2 2 2 2
3 3
```

Its phases were:

1. Actions 1–8 sampled the opaque primitive vocabulary.
2. Actions 9–12 repeatedly tested one falsifiable consequence. Repetition was
   useful here: it was an experiment across changing states, not an open-loop
   macro.
3. Actions 13–24 restored broad coverage while Qwen received the resulting
   criticism and evidence.
4. Action 25 confirmed a uniquely grounded revision connecting `f01` and
   `f02` under a decreasing translation-alignment residual.
5. At action 26, R2—not Qwen—entered control. The selected primitive repeatedly
   reduced the residual; eight exact counterfactual checks showed the selected
   successor was better than the same-state fallback.
6. Actions 37–38 changed primitive when the geometry changed and completed the
   level.

The break-in was therefore not a discovered action chain. It was a mode
transition caused by a grounded explanation becoming unique, prospectively
confirmed, and useful for ranking the next single action.

## What worked

- One-action receding-horizon control preserved responsiveness without an ARC
  point penalty for replanning.
- Separating Qwen semantics from motor authority kept all selected primitives
  deterministic and auditable.
- The scratchpad survived as four bounded, unverified `working_note` objects
  and never gained empirical support.
- Scratchpad validation was decoupled from schema validation. A bad auxiliary
  note can now be rejected without erasing an otherwise valid semantic write.
- Keeping multiple grounded alternatives was useful until evidence supported a
  unique revised binding.
- Repeated actions were allowed when each predecessor state differed and the
  explanation predicted continued progress.
- Environment-authored evidence, not model confidence, drove the switch into
  control.

## What did not work

Two preserved failed runs were informative:

- `artifacts-failed-action24/`: storing the scratchpad through generic semantic
  derivation provenance polluted the inherited causal-chain selector. Working
  memory now has its own object path and no semantic derivation.
- `artifacts-failed-stall-action43/`: scratchpad failure originally invalidated
  the whole Qwen response, delaying grounding and leaving three ambiguous
  bindings. The run cycled. The fixed compiler treats memory and semantic
  claims as independent products.

The first persistence identity for objectives also omitted the plan ID. When a
workspace state recurred, immutable-object validation correctly rejected the
changed payload. Objective and explanation identities now include their plan.

The wall/no-visible-change mechanism passed its focused unit test but was not
exercised by the successful `ar25` trajectory: all 38 observations changed.
It should therefore be described as implemented, not empirically validated on
this game. A no-change observation is retained as an outcome; only an
identical state–primitive retry is suppressed when another untried primitive
exists. Repetition across changed states remains legal and was essential here.

## Cost

The solve took about 500 seconds, including 179 seconds of Qwen latency. The
final graph held 15,857 objects, chiefly 9,746 `r2_binding` and 2,432 `shadow`
objects. This does not spend ARC actions, but late decision cycles become too
slow for a pleasant arcade. The next implementation step should compact or
incrementally update those derived objects while retaining the causal ledger
and the small live inspection projection.
