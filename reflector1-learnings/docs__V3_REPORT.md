# V3 ambiguity-tolerant transfer report

## Outcome

The preregistered blind verdict is **SUPPORTED** for this synthetic game
family. V3 solved 7 of 8 fresh blind pairs (87.5%); the E2 exact-unique-template
baseline solved 6 of 8 (75%). V3 repaired both E2 uniqueness failures, rejected
at least one false mapping from edge-local evidence, and introduced zero
regressions on the learned level.

This is evidence for the specified bounded transfer mechanism. It is not
evidence of broad ARC-AGI-3 competence. The one genuine-novelty blind pair was
not solved by V3, which marks a concrete boundary of the present system.

## Scientific lifecycle

The earlier V2 blind experiment remains `INCONCLUSIVE`: its single blind run
failed an exact visual-role uniqueness prerequisite. Those results were used
only for a labeled V3 postmortem development repair. V3 then used a new clean
lifecycle with disjoint development (5101--5104), validation (6101--6104), and
blind (7101--7108) seeds.

The V3 preregistration was frozen before blind generation:

- preregistration SHA-256:
  `d8911746083e2a71cbd01792ba4c6b05fbfb9766f8fd176cac1983a5049f56bf`
- frozen implementation SHA-256:
  `ef1208bc2385e8245292ffaf4a46064ecfd48d26a4b5a763a9cf75e3143e9981`
- selected validation trace SHA-256:
  `d7908fc6eb21f0820c908c61c9015705e411c6498a89ad942fdb5cdab2a6943b`
- one blind trace SHA-256:
  `b73ba65af1a8c2d0a6a198cc7857f803b33032671bb446a6b2b0c2b4597ed9ea`

The blind split was generated once and executed once after validation sealing.
Post-hoc control labels were revealed only in the saved results after execution.

## Blind outcomes

| Pair | Post-hoc control | E2 | V3 | V3 phase | Actions | Rejected hypotheses |
|---|---|---:|---:|---|---:|---:|
| 01 | related | fail (uniqueness) | pass | accommodation | 7 | 4 |
| 02 | surface decoy | pass | pass | zero-shot | 2 | 0 |
| 03 | structural near-match | pass | pass | zero-shot | 2 | 0 |
| 04 | reversed relation | pass | pass | accommodation | 6 | 2 |
| 05 | extra condition | pass | pass | structural probing | 2 | 0 |
| 06 | genuine novelty | pass | fail | none | 11 | 7 |
| 07 | related | fail (uniqueness) | pass | structural probing | 2 | 0 |
| 08 | combined decoy | pass | pass | accommodation | 7 | 4 |

All four frozen clauses held: higher V3 final success, at least one repaired
uniqueness failure, no excess regression, and explicit false-mapping rejection.

## Algorithm and determinism

V3 keeps a version space instead of requiring a unique visual grounding. A
weighted CSP ranks grounded action-role correspondences by hard violations,
declared loss, slippage count, and stable candidate identifier. Bounded
Hofstadter-style slippage permits neighboring evidence carriers and a costed
unmarked legal action. Active probes prune only falsified edges; absence of a
visible first-edge carrier remains defeasible until positive evidence exists.
Categorical transport is accepted only after its declared consequences are
observed. Otherwise, a bounded accommodation may commit either a directly
verified two-edge adapter or an explicitly recorded complete action strategy.
Every commit is followed by regression replay.

Independent evaluations use immutable inputs and outputs. Worker seeds are
derived from the run seed and candidate ID. Results are stably sorted before a
single coordinator transaction. Process execution is an optional acceleration;
small batches remain serial after an overhead threshold. The run manifest
records requested/effective execution modes and workers. Unit and integration
tests verify serial/process action and Mind equivalence.

## Reproduce and inspect

The blind trial is consumed and should be treated as immutable. Inspect its
saved verdict and replay its canonical trace:

```bash
python3 -m evaluation.v3_experiment report \
  --results experiments/v3_ambiguity_transfer/clean_panel/blind/run-001/results.json

python3 -m dashboard.server \
  --trace experiments/v3_ambiguity_transfer/clean_panel/blind/run-001/trace.json \
  --results experiments/v3_ambiguity_transfer/clean_panel/blind/run-001/results.json \
  --port 8767
```

Open <http://127.0.0.1:8767>. Pair and condition selectors synchronize the full
9x13 board, action timeline, schema/version-space events, rejected hypotheses,
predictions, mismatches, Mind updates, dependency graph, and raw event
inspector. Playback ranges from 4x to a human-watchable 0.05x. The UI consumes
the same append-only events as the runtime and cannot alter agent decisions.

Run the implementation checks with:

```bash
python3 -m pytest -q
```
