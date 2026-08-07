# Grand all-level directed transfer experiment

## Scope

This retrospective experiment inventories every locally executable synthetic
level, deduplicates specifications by content hash, and evaluates every ordered
source-target pair. It contains:

- 20 transfer-atlas levels;
- 32 V2-frozen development, validation, and former-blind levels;
- 32 V3-clean development, validation, and former-blind levels.

That yields 84 levels and 7,056 directed cells. Historical blind levels are
already revealed, so this is exploratory analysis—not a new blind result or an
official Kaggle score. Older manifest-only fixtures lack executable
specifications and are excluded rather than reconstructed from hidden data.

## Results

| Measure | All cells | Valid cells |
|---|---:|---:|
| Cells | 7,056 | 6,972 |
| Completed | 6,752 | 6,752 |
| Completion | 95.69% | 96.84% |
| Zero-shot | 38.05% | 38.51% |
| Mean transfer score | 0.5380 | 0.5445 |
| Prior-level regressions | 0 | 0 |

Solution phases across all cells:

- zero-shot: 2,685 (38.05%);
- structural probing: 1,967 (27.88%);
- accommodation: 2,100 (29.76%);
- valid but unsolved: 220 (3.12%);
- invalid source development: 84 (1.19%).

The transfer score is stricter than completion: completion is multiplied by
squared two-action efficiency, reuse-phase credit, and structural-edit
retention. Consequently, search-heavy accommodation does not masquerade as
strong knowledge transfer.

## Main findings

Transfer-score variance decomposes into 18.6% learned-source effect, 37.4%
target difficulty, and 44.0% source-target interaction. Target structure and
the particular analogy correspondence matter substantially more than choosing
a universally strong source.

Directionality remains high: the mean absolute difference between `i -> j` and
`j -> i` is 0.4236. This is expected for causal schemas, but the magnitude
shows that correspondence search is still brittle.

The V2-frozen sources generalize best on average: 96.73% valid completion,
43.45% zero-shot, and 0.5846 transfer. Atlas sources achieve 97.56%, 40.48%,
and 0.5652. V3-clean sources achieve 96.51%, 32.14%, and 0.4898 after excluding
the invalid source row. The later corpus is harder and includes more
conditional/motion novelty; “newer experiment” therefore does not imply
“easier source representation.”

The best source is G015, a related atlas-B level: 0.7981 mean transfer and
63.1% zero-shot over 84 targets. The worst valid source is G050, a
genuine-novelty V2 validation-B level: 0.1076 mean transfer and 1.19%
zero-shot. G076 is not a valid source at all under the fixed development
budget.

## Failure anatomy

All 84 invalid cells form the G076 source row. G076 is the motion-based
genuine-novelty B level from V3 development seed 5104. Developmental
exploration cannot solve it within eight actions, so no evidence-supported
two-edge diagram can be frozen. This is a goal/exploration failure before
transfer begins.

Among valid cells, the 220 failures concentrate in:

- `extra_condition`: 67;
- `genuine_novelty`: 53;
- `reversed_relation`: 44;
- `related`: 33;
- `structural_near_match`: 10;
- `surface_decoy`: 9;
- `combined_decoy`: 4.

The hardest targets are G032 (genuine novelty), G060 (reversed relation), G064
(genuine novelty), and G062 (extra condition). G060 and G064 each defeat 29
valid sources; G062 defeats 28.

Only 81 of 84 diagonal cells solve. G076 is invalid; G010 and G062 are valid
but fail self-transfer, and both are extra-condition B levels. Thus even an
identical rendered source/target does not guarantee replay: the present
grounding objective can spend its budget testing lower-value correspondences.

## Implications for top-100

The grand matrix strengthens confidence that the candidate/version-space
machinery is real: thousands of directed transfers complete without regression
and source identity measurably affects results. It also identifies the next
work more sharply than another larger synthetic matrix would:

1. add conditional predicates and motion/change schemas to the primitive
   closure;
2. separate goal discovery from two-edge action grounding;
3. rank probes by expected information gain per action;
4. learn a reliability prior over source schemas from row performance;
5. add a source-free baseline to estimate causal transfer gain;
6. move the same protocol to distinct game families and official ARC-AGI-3
   development environments.

The current system is a capable within-family adapter, but only 38.5% of valid
cells solve zero-shot and almost 30% require costly accommodation. Those are the
numbers that must improve for action-efficient Kaggle performance.

## Artifacts

- `experiments/grand_transfer/run-001/results.json`: complete metrics,
  provenance, and four 84x84 matrices;
- `experiments/grand_transfer/run-001/cells.csv`: 7,056 flat cell records;
- `*_matrix.csv`: completion, zero-shot, action-efficiency, and transfer
  matrices;
- `experiments/grand_transfer/run-001/trace.json`: 162 MB canonical event
  stream;
- `experiments/grand_transfer/run-001/report.md`: generated aggregate report.

Trace hash:
`a58d9c5f5159674f0db67f85031ddc140a86415612f54a38a248c1da8d4b776c`.
