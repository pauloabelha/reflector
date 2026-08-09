# Goal-agnostic cross-game test v2 status

- Frozen metadata-only target: `ls20-9607627b`.
- Uses unchanged v6-regressed calibration + v5 semantics/control.
- No target observation has been used for adaptation.

## Frozen run — valid FAIL

- Goal-agnostic calibration completed and all four actions changed the frame,
  but component anchors remained fixed because the small controlled sprite was
  visually connected to a large scene component.
- Translation-only component tracking exposed no controlled candidate;
  `progress_opportunity_present=false`; Qwen validly abstained after four
  actions. No level completed.
- Post-run development diagnosed the missing substrate as pixel-level motion
  inside connected scenery. ls20 is now consumed development data.
