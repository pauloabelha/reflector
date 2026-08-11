# Status

Complete and frozen after the decisive A/B/C run.

- Manifest: `14ebed7872bba10980b79208f0666f437dae576683f021dde2df7754bb2ffb01`
- Controls: passed
- Regression tests: 32 passed
- A: 1 level in 38 actions
- B: abstained at action 0
- C: abstained at action 0; Python available but not executed
- Exact replay: all arms
- Support-authority violations: 0 in all arms

The architecture held: in B/C only QwenExecutor produced concrete proposals,
the arbiter alone could commit, and neither R2 nor semantic Qwen acted as a
competing policy head. The scientific result is negative for B > A and
negative by intention-to-treat for C > B; the code-mediated mechanism remains
unidentified because C did not engage the tool.
