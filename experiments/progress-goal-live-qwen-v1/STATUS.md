# Live progress-goal reconstruction v1 status

- Protocol and experiment frozen before first Qwen/environment run.
- Input: empty workspace, current frame, generic grounded region census,
  equivalence/capacity hypotheses, and one common calibration transition per
  opaque intervention.
- Output: at most one support-zero goal from six generic families.
- No oracle goal, binding, action meaning, or action sequence enters the run.
- Pre-run protocol plus intervention regression suite: 26 tests pass.

## Fresh run 1 — valid FAIL

- Qwen received the fresh frame and live calibration workspace; transport and
  grammar were valid (945 prompt tokens, 1,555 completion tokens).
- It explicitly identified the controlled singleton, the exact repeated class,
  and the exact-capacity three-member region in its reasoning, but returned an
  abstention after becoming distracted by a second advertised capacity object.
- That distractor was a thin full-frame boundary strip. The workspace had
  inferred capacity from area equality alone even though the member shape could
  not tile the strip. This is a generic capacity-grounding bug.
- Reasoning also ended mid-comparison at the frozen thinking budget. No goal was
  written and the episode stopped after the five calibration actions at level0.
- v1 is preserved as FAIL. Any repair is a separately versioned experiment.
