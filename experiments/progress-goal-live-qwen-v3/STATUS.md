# Progress-seeking live goal reconstruction v3 status

- Frozen after the v2 abstention.
- Only changes: exact current inside/outside counts, generic progress-seeking
  proposal obligation, and bounded reasoning/output allocation.
- No prior Qwen semantic content enters the request.

## Fresh run 1 — semantic success, control FAIL

- Qwen wrote the correct support-zero family, members, container, potential, and
  terminal: `OutsideCount({f00,f01,f03},f05) -> AllInside`.
- It incorrectly bound `controlled_id=f05` even though all calibrated motion
  belonged to `f02`, and chose translating `im00` as the interaction candidate
  instead of the still-unexplained zero-effect intervention.
- The v3 compiler checked visible addresses but not consistency with grounded
  transition evidence, so the malformed ports reached the planner. The factual
  run replayed exactly but remained level0 after 28 actions.
- v3 is preserved as FAIL. v4 must return an exact R2 criticism to Qwen and
  require Qwen—not the runner—to revise those ports.
