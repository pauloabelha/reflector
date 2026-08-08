# Results: R2 25-Game Context Spinoff Diagnostic

## Status

Interim results as of `2026-08-08T00:15:05-03:00`. The preregistered full
25-game parallel run is still active, so cohort aggregates, the per-game table,
the serial/parallel identity result, and the final verdict are not yet
available. This section reports only results already verified from completed
commands; it does not estimate results retained inside running workers.

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

The complete repository test suite also passes: `63 passed`.

## Active full-cohort run

The fixed 25-game run started at approximately
`2026-08-07T22:29:24-03:00` with seed `0`, `24` process workers, maximum `64`
executed action changes per game, minimum context support `2`, and no changes to
the preregistered candidate language, ranking rules, purity threshold, or
promotion gate.

At this interim checkpoint, live matched branch execution has been observed in
at least six independent games: `ar25`, `g50t`, `ls20`, `m0r0`, `re86`, and
`tr87`. This is a lower bound on games reaching executed branches, not a cohort
metric. No worker crash, predecessor replay mismatch, or parent-integrity
failure has been emitted. The runner intentionally writes aggregate artifacts
only after all game workers return, so no partial precision or regression rate
is currently available.

## Verdict

Pending. `PROMOTE`, `CONTINUE-DIAGNOSTIC`, or `REJECT` will be assigned only
after the complete fixed cohort and exact serial/parallel identity check.
