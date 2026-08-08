# Results: R2 25-Game Context Spinoff Diagnostic

## Status

Interim results. The table and aggregate below cover the 11 games with durable
completed checkpoints. The final 25-game parallel aggregate and final verdict
are not yet available. This report contains only results verified from
completed commands; it does not estimate results retained inside running
workers.

After reviewing the measured CPU cost, the user explicitly directed the run to
stop after the parallel track and not execute the multi-day full-cohort serial
replay. The passing deterministic serial/parallel worker harness remains part
of the safeguard evidence, but the final report will not claim an exhaustive
25-game serial identity comparison.

## Frozen `ar25` sanity check

The generic diagnostic runner reproduced the previously demonstrated case on
an 18-packet chronological prefix without a game-specific candidate or branch:

- context schema: `38bac99b151198744c9ea62355a77c6116ef9493de6e678115dc8d4772385454`;
- parent schema: `4dd44c2c187a681e2c8079ec0c9c79bcdc599b87829ea73cf326c5df191e23cc`;
- specialized child: `e4d3812a7ae5f3c0efd59918f0d45ca3218e167384dd1e3fb8f88843d8b197b0`;
- parent top action `2`, child top action `3`;
- matched control completed-level delta `0`;
- matched spinoff completed-level delta `+1`;
- frozen matching opportunity: `ar25:16:e4d3812a7ae5`.

The prefix produced two eligible opportunities, two top-action changes, and two
executed matched comparisons. The frozen opportunity was one of them. Prefix
evaluation took 82.64 wall seconds and 84.58 CPU seconds.

## Safeguards

All five experiment-specific safeguards pass:

1. context discovery has no held-out successor/action input;
2. candidate context and child construction contain only generic relational
   structure, without game/level IDs or prohibited semantic labels;
3. spinoff construction preserves the parent's atoms and canonical hash;
4. ordered serial and multiprocessing results are identical in the worker
   harness;
5. each job starts with an isolated R2 runtime and kernel state.

The checkpoint safeguard added after the first interrupted run also passes.
The complete repository test suite now passes: `69 passed`.

## Full-cohort execution history

The fixed 25-game run started at approximately
`2026-08-07T22:29:24-03:00` with seed `0`, `24` process workers, maximum `64`
executed action changes per game, minimum context support `2`, and no changes to
the preregistered candidate language, ranking rules, purity threshold, or
promotion gate.

During the first attempt, live matched branch execution was observed in
at least six independent games: `ar25`, `g50t`, `ls20`, `m0r0`, `re86`, and
`tr87`. This is a lower bound on games reaching executed branches, not a cohort
metric. No worker crash, predecessor replay mismatch, or parent-integrity
failure was emitted.

That attempt was terminated by an execution-session boundary after about five
hours, before the original all-at-once artifact writer ran. It therefore
produced no defensible cohort aggregate. This exposed a reliability defect in
the experiment runner, not an experimental outcome. The runner now writes each
completed game to an atomic, input/configuration-keyed checkpoint and resumes
only missing games. The protocol, candidate language, thresholds, action
ranking, matched control, and promotion gate were not changed.

## Durable partial cohort result

As of `2026-08-08T17:10:06-03:00`, the resumed parallel run remains active and
has atomically completed 11 of 25 games. These games are an arrival-order subset,
not a representative sample, so they are reported descriptively and are not
used to assign a verdict:

| Game | Transitions | Opportunities | Children | Top changes | Executed changes | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ar25` | 399 | 372 | 5 | 20 | 6 | 4 improve, 2 tie, 0 worsen; level delta +1 |
| `cd82` | 98 | 25 | 2 | 2 | 0 | both changes abstained: action data required |
| `cn04` | 399 | 0 | 0 | 0 | 0 | no eligible relational context |
| `ft09` | 161 | 0 | 0 | 0 | 0 | parent was never genuinely ambiguous |
| `ka59` | 399 | 0 | 0 | 0 | 0 | no eligible relational context |
| `sb26` | 123 | 113 | 1 | 0 | 0 | child never changed the top action |
| `sc25` | 399 | 0 | 0 | 0 | 0 | no eligible relational context |
| `sp80` | 399 | 202 | 4 | 5 | 0 | all changes abstained: action data required |
| `su15` | 399 | 0 | 0 | 0 | 0 | no eligible relational context |
| `tu93` | 399 | 0 | 0 | 0 | 0 | no eligible relational context |
| `wa30` | 399 | 0 | 0 | 0 | 0 | no eligible relational context |

Across this partial subset there are 712 eligible opportunities, 12 children,
27 top-action changes, and 6 executed changes. The provisional action-changing
precision is 4/6 (66.7%): 4 improve, 2 tie, and 0 worsen, with completed-level
delta +1. All executed comparisons and all observed benefit are currently
concentrated in `ar25`, however, so this partial result does not satisfy the
cross-game promotion requirement. The two additional changed actions in
`cd82` and five changes in `sp80` were prospectively abstained rather than
forced through an unsupported evaluator path.

### Interim metric detail

- processed data: 3,585 packets and 3,574 chronological transitions;
- games with an eligible opportunity: 4/11 (`ar25`, `cd82`, `sb26`, `sp80`);
- action-changing precision: 4/6 (66.7%);
- false-spinoff rate: 0/6 (0%);
- completed-level/progress delta versus matched control: +1;
- score delta: unavailable because the offline observation API exposes no
  per-step score;
- structural prediction after an executed change: child 6/6 reified, parent
  3/6 reified and 3/6 refuted;
- child mean stated confidence: 1.000, with empirical reification 1.000;
- parent mean stated confidence: 0.953, with empirical reification 0.500;
- forward transition-micro accuracy: 1.000; forward game-macro accuracy: 1.000,
  but over only the single game with executed changes;
- inverse accuracy: not applicable because the mechanism has no inverse action
  decoder;
- parent integrity: intact in all 11 completed games.

Abstentions across the completed transitions are 2,620 `no-eligible-context`,
242 `parent-not-ambiguous`, and 21 `action-data-required`. These are deliberate
protocol gates, not failed comparisons.

### Concentration and negative results

The interim result is highly concentrated. `ar25` supplies 52.2% of all
opportunities, 74.1% of top-action changes, and 100% of executed changes and
benefits. This concentration is the main reason the current evidence cannot
support promotion even though the observed precision clears the numerical
precision threshold.

Six completed games have no eligible relational context: `cn04`, `ka59`,
`sc25`, `su15`, `tu93`, and `wa30`. `ft09` never reaches genuine parent ranking
ambiguity. No executed spinoff has made behavior worse so far. Three context
hashes recur independently across games (`ar25`/`cd82` and `ar25`/`sp80`), so
the discovered relations are not all game-unique; nevertheless, no recurring
context has yet produced an executable benefit outside `ar25`.

Absence conditions currently dominate: 420/712 opportunities (59.0%), 18/27
top-action changes (66.7%), and all 6 executed changes use an absent relation.
They do not dominate initial child creation, where 5/12 children are absence
conditions and 7/12 are presence conditions. Three minimum-support contexts
occur in only one completed game and remain plausible accidental/overfit
contexts pending the full cohort.

Compact executed examples all preserve parent
`4dd44c2c187a...`: absent `SameInteriorContrast` creates child
`e4d3812a7ae5...`, and absent `DifferentInteriorContrast` creates child
`c93cecb6794f...`; both rerank opaque action `2` to `3`. Across six matched
executions these two children yield four improvements and two ties.

### Provisional interpretation

The strongest defensible reading is: the frozen mechanism is real and
reproducible in `ar25`, its abstention behavior has prevented observed
regressions in the completed subset, and some relational contexts recur across
independent games. The missing evidence is breadth. Until beneficial executed
changes occur in at least two more independent games, the preregistered
cross-game promotion gate cannot pass.

## Verdict

Provisional: `CONTINUE-DIAGNOSTIC`. The final `PROMOTE`,
`CONTINUE-DIAGNOSTIC`, or `REJECT` verdict will be assigned after the complete
fixed-cohort parallel run. A full-cohort serial identity replay was explicitly
waived; only the passing serial/parallel deterministic harness will be reported.
