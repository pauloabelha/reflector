# Reflector Schema Calculus

This is a clean-room, Kaggle-first vertical slice of an LLM-free and neural-free
ARC-AGI-3 agent. Every executable cognitive object is a typed `Schema[A, B]`.
The current implementation demonstrates typed composition, products,
quotation/evaluation, audited primitives, one causal prediction confirmation
followed by a controlled failure, explicit evidence updates, a failed diagram,
a transactional rewrite, an immutable serialized Mind, deterministic replay,
legal action selection, exact structured traces, a live/replay dashboard, and
optional deterministic multiprocessing for candidate evaluation.

It is a research scaffold, not evidence of ARC-AGI-3 competence. The included
synthetic environment proves runtime invariants only.

```bash
python3 -m pytest
python3 -m evaluation.replay --output /tmp/reflector-demo
python3 -m submission.smoke_test
```

## Kaggle score release

The exact locally validated v164 competition notebook is staged in
`submission/kaggle_v164/`. It embeds candidate
`candidate-df8025bb91c33a59` and its fingerprint-matched inference closure.
The release reproduced `25.959943125184374/100` across all 25 public
development games (62/183 levels and 5 completed games) before upload.
See `submission/kaggle_v164/release-manifest.json` for immutable hashes and
Kaggle run/submission identifiers.

## Watch a live episode

Start the dashboard and its deterministic full-board visual episode with one command:

```bash
python3 -m dashboard.server \
  --live-board \
  --output artifacts/live/trace.json \
  --step-delay 0.35
```

Open <http://127.0.0.1:8765>. The episode begins on the first dashboard/API
view. The UI follows the append-only event stream as the unchanged runtime
policy acts. Pause stops the UI from following the newest step so it can be
audited; it does not interfere with or alter the running agent.

The large board shows the agent moving through a complete route, collecting
progress markers, changing direction, and reaching the goal. Directional
action names are UI annotations only; the runtime and canonical trace retain
the same opaque integer action identifiers used by the policy. For the minimal
1x2 developmental invariant fixture, use `--live-synthetic` instead.

The completed canonical replay is saved at `artifacts/live/trace.json`. Replay
that exact stream with:

```bash
python3 -m dashboard.server --trace artifacts/live/trace.json
```

The browser provides play, pause, previous, single-step, timeline, and buffered
viewing-speed controls in both live and replay modes. The default is a
human-watchable 0.5x (two seconds per action), with options down to 0.05x
(twenty seconds per action). Changing viewing speed never changes runtime
timing, policy decisions, or the canonical trace. Synchronized frames, actions, typed schemas, action and rewrite
candidates, real predictions/comparisons, evidence counters and confidence,
failed diagram, committed Mind changes, budget, activation graph, and raw events
are all projections of the same runtime trace.

The deployed path and dashboard have no runtime dependency beyond Python's standard library.
See `docs/DSL_SPEC.md`, `docs/ARCHITECTURE.md`, and `docs/FIREWALL.md`.

## Run the preregistered two-level experiment

The first operational categorical experiment uses a frozen same-`k` synthetic
pair and matched O/M/Q/R/E candidate budgets. It runs overfit, compression,
equilibrium rewriting, bounded composition, quote/eval reification, frozen-Mind
zero-shot transfer, diagram correspondence, minimal accommodation, and Level A
regression replay through actual DSL and immutable Mind transactions:

```bash
python3 -m evaluation.two_level_experiment --output artifacts/two-level-v1
python3 -m dashboard.server --trace artifacts/two-level-v1/trace.json --port 8766
```

Open <http://127.0.0.1:8766>. The dashboard experiment table and raw trace are
projections of the saved append-only events. The frozen preregistration is
[`evaluation/two_level_preregistration.json`](evaluation/two_level_preregistration.json),
and the scientific report is written to `artifacts/two-level-v1/result.json`.

This one synthetic pair tests the mechanism and supports a verdict only for the
preregistered experiment. It is not evidence of ARC-AGI-3 competence or broad
cross-game generalization.

## V2 discovered multi-step transfer panel

The versioned V2 experiment lives under
`experiments/v2_discovered_transfer/`. Its create-once lifecycle commands are:

```bash
# Generate the non-blind frozen family.
python3 -m evaluation.v2_game_family --split development
python3 -m evaluation.v2_game_family --split validation

# Development and validation panels.
python3 -m evaluation.v2_panel run --split development \
  --output experiments/v2_discovered_transfer/development/run-003 \
  --mode process --workers 4
python3 -m evaluation.v2_panel run --split validation \
  --output experiments/v2_discovered_transfer/validation/run-001 \
  --mode process --workers 4

# Freeze validation-selected weights, stopping rules, budgets, and source hashes.
python3 -m evaluation.v2_panel seal-validation \
  --results experiments/v2_discovered_transfer/validation/run-001/results.json

# One permitted blind generation and execution, only after the freeze.
python3 -m evaluation.v2_game_family --split blind --allow-blind
python3 -m evaluation.v2_panel run --split blind \
  --output experiments/v2_discovered_transfer/blind/run-001 \
  --mode process --workers 4

# Produce the frozen aggregate artifacts and report.
python3 -m evaluation.v2_report report
```

Frozen artifacts refuse overwrite. In this checkout the blind commands have
already been consumed: generation succeeded, but the single blind execution
failed its role-discovery prerequisite. Do not rerun them. The preregistered
primary verdict is therefore `INCONCLUSIVE`; see
`experiments/v2_discovered_transfer/reports/final_report.md`.

Replay the completed validation panel and watch one pair/condition by selecting
it in the dashboard:

```bash
python3 -m dashboard.server \
  --trace experiments/v2_discovered_transfer/validation/run-001/trace.json \
  --results experiments/v2_discovered_transfer/validation/run-001/results.json \
  --port 8766
```

The V2 view expands the exact recorded transitions into full 9×13 before/after
boards. It adds curriculum, pair and condition filters, phase/role timelines,
multi-edge correspondence evidence, rejection outcomes, cost decomposition,
and aggregate comparison. Latent environment roles are removed by default;
`--show-posthoc` enables them only for an explicitly post-hoc audit. Playback
speed includes 0.05×, and play, pause, previous-step, single-step, and timeline
controls never alter the trace or policy decisions.

## V3 ambiguity-tolerant transfer

V3 implements the complete developmental pipeline:

```text
overfit -> compress -> decompose -> equilibrate -> compose -> reify -> freeze
        -> weighted-CSP grounding/version space -> bounded slippage
        -> active probes -> categorical transport verification
        -> minimal accommodation -> regression replay -> transactional commit
```

Candidate generation and evaluation are pure, immutable
`CandidateInput -> CandidateResult` operations. Optional process workers derive
their seeds from the run seed and stable candidate identifier; only the
coordinator ranks results, chooses an action, and commits the new Mind. Tests
require serial and process modes to produce the same decisions.

The clean experiment was preregistered and frozen before generating seeds
7101--7108. Its one blind execution is complete. V3 solved 7/8 pairs (87.5%)
versus 6/8 (75%) for the exact-unique-template E2 baseline, repaired both E2
uniqueness failures, rejected false mappings, and caused no prior-level
regressions. The preregistered verdict is `SUPPORTED`. One genuine-novelty pair
remained unsolved, so this supports the bounded mechanism tested here rather
than universal cross-game transfer.

Watch the complete blind trace, including full boards, actions, grounding
hypotheses, probes, rejected candidates, accommodation, and raw events:

```bash
python3 -m dashboard.server \
  --trace experiments/v3_ambiguity_transfer/clean_panel/blind/run-001/trace.json \
  --results experiments/v3_ambiguity_transfer/clean_panel/blind/run-001/results.json \
  --port 8767
```

Open <http://127.0.0.1:8767>, choose a pair and V3 condition, and select 0.05x
for twenty seconds per action. The dashboard is a read-only projection of the
same append-only Kaggle-compatible trace; it never invokes or changes policy
code. See [`docs/V3_REPORT.md`](docs/V3_REPORT.md) for the protocol, hashes,
per-pair outcomes, limitations, and reproduction commands. The consumed blind
run must not be rerun as a second confirmatory trial.

## Real ARC-AGI-3 game-level matrix

Build the real 25-game by level outcome matrix from the frozen official local
run and the installed ARC-AGI-3 public environments with:

```bash
python3 -m evaluation.real_arc_level_matrix \
  --output experiments/real_arc_level_matrix/run-001 \
  --arc-root ../arc-agi-3-public-games-2026
```

The command validates all scorecard game/version identifiers against the local
ARC download manifest, API metadata, environment metadata, and executable game
source. It writes one row for every real level plus completion, reached,
official-score, action, baseline-action, and efficiency matrices. This is
observed public-development evidence. It is deliberately separate from the
synthetic source-to-target atlas: causal transfer on real games requires
controlled prior/reset executions in the official environments.

## Directed transfer atlas

Run the exploratory 20x20 source-level to target-level transfer matrix with:

```bash
python3 -m evaluation.transfer_matrix \
  --output experiments/transfer_atlas/run-001 \
  --size 20 --seed 9000 --run-seed 9100 \
  --mode process --workers 4
```

This produces 400 independently replayable cells, `results.json`, `cells.csv`,
a complete append-only `trace.json`, and a Markdown heatmap/report. Every cell
records completion, zero-shot completion, squared action efficiency, normalized
transfer score, phase solved, action/edit cost, rejected hypotheses,
regressions, and its deterministic worker seed. Whole cells are immutable
parallel tasks; the coordinator alone sorts and writes results. This is an
exploratory breadth experiment within the current procedural family, not a
substitute for an official Kaggle-game score.

The completed run is summarized in
[`docs/TRANSFER_ATLAS_REPORT.md`](docs/TRANSFER_ATLAS_REPORT.md). Inspect any
source-to-target cell visually with:

```bash
python3 -m dashboard.server \
  --trace experiments/transfer_atlas/run-001/trace.json \
  --results experiments/transfer_atlas/run-001/results.json \
  --port 8768
```

## Grand all-level experiment

Inventory, content-deduplicate, and run every compatible local level against
every other level:

```bash
python3 -m evaluation.grand_transfer_experiment \
  --output experiments/grand_transfer/run-001 \
  --run-seed 9200 --mode process --workers 4
```

The current executable corpus contains 84 unique levels—32 V2-frozen, 32
V3-clean, and 20 transfer-atlas levels—so this evaluates 7,056 directed cells.
It includes revealed historical development, validation, and blind levels and
is therefore explicitly retrospective exploratory analysis, not a fresh blind
experiment. Older manifest-only fixtures are inventoried but cannot be executed
without reconstructing hidden specifications, so they are correctly excluded.

The completed results and interpretation are in
[`docs/GRAND_TRANSFER_REPORT.md`](docs/GRAND_TRANSFER_REPORT.md). Full matrices
are also exported as CSV for heatmaps and statistical analysis.

## Causal transfer benchmark

The preregistered S0/M/E benchmark is complete. It compares an exactly empty
source-free Mind (S0), compression-only source development (M), and the frozen
full developmental treatment (E) under identical target resource maxima. The
independent Pulse World family adds moving persistent state, delayed effects,
partial observability, and state-dependent opaque action semantics. Development
and validation were sealed before the eight blind pairs were generated, and the
blind panel was executed once.

Watch the full 12×13 boards and every recorded action, or filter by target,
source, and condition in the causal benchmark view:

```bash
python3 -m dashboard.server \
  --trace experiments/causal_transfer_benchmark/independent_family/blind/run-001/trace.json \
  --results experiments/causal_transfer_benchmark/independent_family/blind/run-001/results.json \
  --benchmark-report experiments/causal_transfer_benchmark/reports/aggregate_summary.json \
  --port 8769
```

Open <http://127.0.0.1:8769>. The same play, pause, previous, single-step,
timeline, and 0.05× human-watchable speed controls apply. The benchmark panels
show source-free comparison, phase, target and developmental resources,
transported diagrams, every probe-objective term, adaptation complexity,
regression status, causal deltas, aggregate S0/M/E distributions, source
selection comparisons, and raw canonical events. This is a read-only trace
projection; it never invokes policy code.

The frozen verdicts are `NOT SUPPORTED` for prior-source value, full-treatment
value, and cross-family survival. E won five targets and tied three, but its
median E−M and E−S0 gain was +0.021159, below the preregistered +0.05 margin.
See
[`experiments/causal_transfer_benchmark/reports/final_report.md`](experiments/causal_transfer_benchmark/reports/final_report.md)
for the full interpretation and artifact index. These synthetic results make no
claim of official ARC or Kaggle competence.
