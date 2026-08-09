# Qwen semantics with R2-grounded open ports v5 status

- Frozen after v4 revision failure.
- No semantic field is corrected by R2; only exact controlled/intervention ports
  may be reopened and uniquely grounded from visible calibration facts.
- No prior Qwen response enters this fresh run.

## Fresh run 1 — PASS

- Qwen independently wrote the correct support-zero semantic object:
  `OutsideCount({f00,f01,f03},f05) -> AllInside`.
- Qwen's contradicted concrete ports were preserved. R2 reopened and uniquely
  grounded them to controlled region `f02` and unexplained intervention `im04`
  from the complete calibration stream.
- The grounded workspace object completed level1 in 33 total actions, under the
  40-action gate. Exact factual replay and final digest matched.
- Qwen prompt/completion/total tokens: 1,077 / 2,185 / 3,262; latency 32.45s.
- Empirical support remained zero at proposal/grounding; completion was decided
  by the environment.

This establishes live semantic construction plus R2 grounding on a consumed
development game. It is not cross-game generalization.
