# Public 25-game first-frame evaluation

> **Current configuration update (2026-08-07).** The tables below preserve the
> original shallow-discovery baseline. The default runtime now uses four
> bounded composition rounds (256 proposals total) plus generic relational
> closure, and the evaluator uses all CPU cores by default (`--workers 0`). On
> the same 25 unique recordings, the current run succeeds on 25/25 frames and
> stays within all active-workspace budgets: 129 reusable candidates total
> (median 4 per game), richer structural candidates in 18/25 games, median 34
> active schemas, maximum 95 active schemas, and maximum 284 active edges.
> The 24-process local run took 0.308 seconds. See
> [`MULTILEVEL_DISCOVERY.md`](MULTILEVEL_DISCOVERY.md) for the current protocol
> and the `ar25` pair-schema oracle.

## Outcome

Reflector-II successfully processed the first observation of all 25 public game
recordings in `reflector-v14-graph-400`. All 25 stayed inside the configured
active-workspace limits and all 25 produced at least one structurally reusable
composite schema with repeated support and an explicit decomposition DAG.

That result has two deliberately separate tiers:

- **Structural reuse: 25/25.** There were 78 reusable candidates in total. All
  had depth greater than zero, at least two uses, a body of at least two atoms,
  and at least one decomposition.
- **Richer-than-shape/type reuse: 3/25.** Fourteen candidates in `g50t`,
  `m0r0`, and `vc33` included attribute or relational structure beyond the
  common `Form` + `Kind` chunk. Examples include `Inside`, `Enclosed`,
  `Connected`, `Color`, and `EnclosureCount` conjunctions.

The first tier is a real representation/runtime pass. It is not yet evidence
that the schemas predict actions, distinguish goals, or solve games. The second
tier shows that the same generic path can extract more semantic conjunctions,
but only on 12% of first frames under the present one-cycle protocol.

## Protocol

- Corpus: the 25 uniquely named `*.recording.jsonl` files in the newer
  `reflector-v14-graph-400` directory. The older duplicate 25-game run was not
  mixed into the sample.
- Input: only the final rendered layer of the first `data.frame` packet. Public
  recordings contain between one and 42 layers in that packet; the final layer
  is the state opened for the next action.
- Knowledge: raw integer grid only. API game metadata and game-specific
  recognizers were not used.
- Execution: a fresh `Runtime` per game, generic connected-region perception,
  and one bounded observation cycle.
- Structural pass: at least one reusable composite, with every reported
  reusable composite satisfying depth > 0, uses >= 2, decomposition count >= 1,
  and body size >= 2.
- Richer pass: at least one reusable composite whose predicate-head set is not
  exactly `{Form, Kind}`. This is a descriptive tier, not a task-relevance
  claim.

## Aggregate measurements

| Measurement | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Facts | 759 | 3,501 | 11,535 |
| Foreground regions | 4 | 24 | 191 |
| Distinct forms | 3 | 8 | 44 |
| Active schemas | 12 | 26 | 75 |
| Active edges | 4 | 36 | 132 |
| Retrieved/verified candidates | 10 | 16 | 51 |
| Composition proposals | 64 | 64 | 64 |
| Retained compositions | 1 | 9 | 32 |
| Reusable candidates | 1 | 3 | 11 |
| Work items | 83 | 153 | 317 |
| Explicit truncation events | 4 | 9 | 74 |

All frames were 64×64. A representative sequential CPU run processed the full
set in 1.36 seconds, with per-frame perception between 3.4 and 28.9 ms and
runtime work between 13.8 and 121.6 ms. Timings are observational, not a
controlled performance benchmark.

## Per-game result

| Game | Facts | Regions | Active schemas | Retained | Reusable | Richer | Truncations |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25 | 1,864 | 12 | 19 | 6 | 2 | 0 | 44 |
| bp35 | 9,763 | 191 | 15 | 4 | 1 | 0 | 74 |
| cd82 | 3,501 | 13 | 27 | 10 | 3 | 0 | 42 |
| cn04 | 1,427 | 7 | 18 | 5 | 1 | 0 | 52 |
| dc22 | 11,535 | 35 | 29 | 10 | 5 | 0 | 4 |
| ft09 | 8,064 | 64 | 28 | 10 | 4 | 0 | 4 |
| g50t | 4,422 | 10 | 49 | 32 | 6 | 4 | 6 |
| ka59 | 3,458 | 14 | 23 | 8 | 4 | 0 | 40 |
| lf52 | 6,335 | 59 | 20 | 5 | 1 | 0 | 4 |
| lp85 | 8,657 | 37 | 23 | 8 | 3 | 0 | 4 |
| ls20 | 6,043 | 19 | 47 | 26 | 2 | 0 | 6 |
| m0r0 | 10,592 | 4 | 37 | 27 | 11 | 8 | 6 |
| r11l | 3,293 | 37 | 23 | 7 | 2 | 0 | 4 |
| re86 | 1,056 | 24 | 19 | 6 | 4 | 0 | 20 |
| s5i5 | 1,336 | 28 | 43 | 18 | 1 | 0 | 12 |
| sb26 | 1,992 | 24 | 29 | 11 | 3 | 0 | 20 |
| sc25 | 2,666 | 22 | 27 | 10 | 3 | 0 | 24 |
| sk48 | 6,945 | 45 | 26 | 9 | 6 | 0 | 4 |
| sp80 | 2,392 | 8 | 21 | 7 | 1 | 0 | 52 |
| su15 | 3,359 | 27 | 19 | 6 | 2 | 0 | 14 |
| tn36 | 4,580 | 48 | 30 | 9 | 4 | 0 | 4 |
| tr87 | 10,424 | 64 | 75 | 24 | 3 | 0 | 4 |
| tu93 | 2,854 | 66 | 12 | 1 | 1 | 0 | 9 |
| vc33 | 6,119 | 11 | 45 | 28 | 3 | 2 | 6 |
| wa30 | 759 | 11 | 21 | 7 | 2 | 0 | 46 |

## Interpretation and next pressure point

The sparse retrieval claim survives this corpus: at most 51 candidates were
retrieved and 75 schemas activated, well below the 256-node and 512-candidate
limits. The system also remains useful on cluttered input: `bp35` has 191
regions but activates only 15 schemas.

The weakness is equally clear. Proposal generation reaches its cap of 64 in
every game, and every game records at least four explicit truncations. The
runtime is bounded, but its current proposal ordering is doing meaningful
selection under constant saturation. More importantly, 64 of 78 reusable
candidates are shape/type chunks. The next scientific test should use short
before/action/after sequences and ask whether learned DAG schemas improve held-
out transition prediction. Increasing the proposal cap alone would make the
run larger without establishing usefulness.

## Reproduce

```bash
PYTHONPATH=src python3 -m reflector2.evaluate_first_frames \
  /home/pauloabelha/arc-agi-3-public-games-2026/recordings/reflector-v14-graph-400 \
  --expected-games 25 --require-useful-every-game
```

The command emits the complete machine-readable report as JSON and exits
unsuccessfully if a frame cannot be evaluated or if the optional all-games
structural criterion is not met.
