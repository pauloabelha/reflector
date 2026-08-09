# Evidence-consistent live goal revision v4

v3 constructed the correct collection goal but supplied two ports contradicted
by the calibration stream. v4 adds no semantic hint and performs no silent
repair. R2 validates the proposal against already observed transitions and
writes a structured criticism when:

- `controlled_id` is not the region whose pose changed under interventions; or
- an alleged interaction candidate already has a known translation effect while
  an unmodelled/zero-effect candidate remains.

The criticism lists the exact offending and admissible visible references with
their observed deltas. Qwen receives its original proposal, that criticism, the
same live workspace, and the current frame. It must emit one complete revised
hypothesis. The original semantic family is not frozen or forced, though an
evidence-consistent revision must pass the same support-zero compiler.

PASS requires an initial rejected proposal, a nonidentical Qwen revision citing
the returned evidence implicitly through corrected ports, environment level 1
completion within 40 actions, and exact replay. A first-pass already-correct
proposal may also pass diagnostically but does not demonstrate revision.
