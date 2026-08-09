# Goal-agnostic cross-game test v2

The v1 cross-game target g50t was opened but no action was taken because the old
calibration required a collection role. v2 uses the successfully regressed v6
goal-agnostic tracker and otherwise unchanged v5 semantic/control stack.

Selection repeats the frozen metadata-only keyboard/hash rule, excluding
`ar25`, `wa30`, and now-consumed `g50t`. The lexicographically smallest hash is
`ls20`, immutable version `ls20-9607627b`. The receipt is fsynced before opening
the environment. No ls20 frame/source/outcome is inspected for adaptation.

PASS requires level1 within 40 actions and exact replay. Missing or ambiguous
control, no progress hypothesis, unsupported family, and no completion are
valid FAIL. Integrity/context/transport/replay faults are INVALID. No target
substitution or in-run repair is allowed.
