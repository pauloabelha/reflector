# Design notes

This experiment deliberately delegates representation and baseline control to
the current implementation:

- `ExplanationEngine.decide` constructs the existing top-8 beam and computes
  Arm A. The experiment does not reproduce its support/risk/progress formula.
- `ProspectivePrediction.signature` supplies ordinary learned transition
  `Change`/`Preserve` commitments. No second predicate language is introduced.
- `Runtime.workspace.activation` is the only consequence frontier. The
  treatment never scans dormant schemas; canonical hashes provide stable IDs.
- `Runtime.learn_transition` evaluates real and copied branch successors. Only
  the chronological call persists; branch calls occur on deep copies.
- the existing public-recording parser and offline ARC replay helpers from the
  context-spinoff diagnostic are imported, rather than duplicated.
- the existing seeded action stream (`arc_harness._derived_seed`) supplies the
  baseline fallback exactly as the harness does.

The only new representation is an immutable experiment-local record containing
an explanation ID, existing schema IDs/hashes, effect atoms, integer evidence,
and a tuple score. It is a trace view over R2 objects, not knowledge.

The richest justified imagined successor is an effect signature. Full future
pixels, coordinates, game roles, semantic labels, goals, action meanings,
multi-step search, and LLM inference are absent. Lack of an exact active
effect-signature consequence match is an epistemic abstention.
