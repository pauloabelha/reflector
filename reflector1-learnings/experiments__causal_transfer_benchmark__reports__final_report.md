# Causal transfer benchmark final report

## Frozen verdicts

- Prior-source verdict — **NOT SUPPORTED**: Compressed source knowledge did not improve blind target transfer relative to source-free learning.
- Full-treatment verdict — **NOT SUPPORTED**: The full treatment did not meet the frozen improvement margin relative to compression alone.
- Cross-family verdict — **NOT SUPPORTED**: The measured transfer gain did not survive the independent family under the frozen margin.

All eight blind targets were valid. The decision margin was fixed at +0.05 median transfer utility before blind generation.

## Blind primary results

| Comparison | Median delta | Mean delta | Win/tie/loss |
|---|---:|---:|---:|
| M − S0 | 0.000000 | 0.000000 | 0/8/0 |
| E − M | 0.021159 | 0.356040 | 5/3/0 |
| E − S0 | 0.021159 | 0.356040 | 5/3/0 |

E completed 8/8 targets, M and S0 each completed 7/8. E won five and tied three against both controls, with no losses or source regressions. Two large action-efficient wins raised E's mean gain to +0.356040, but the preregistered median gain was only +0.021159; therefore the result does not support H2 or H3. M and S0 were identical on every primary target, so H1 is not supported.

## Interpretation

The full treatment sometimes finds highly efficient cross-family correspondences, but the benefit is not broad enough across targets to clear the frozen robust-effect threshold. Compression alone provides no causal value under the primary selector. The oracle E median is 0.85, indicating substantial source-target interaction and a source-selection problem, but oracle performance is analysis-only. Random E exceeded the current online selector in mean and median utility; this is evidence that the frozen applicability ranking is not yet predictive enough, not permission to retune the consumed blind trial.

The existing-family smoke favored E much more strongly (median E−M +0.7875). Its attenuation to +0.021159 on the independent blind family is why the cross-family verdict is NOT SUPPORTED under the preregistered rule.

## Protocol integrity

- S0 began with an exactly empty learned Mind and was evaluated once per target.
- M and E shared identical source experience before development diverged.
- All conditions used the same frozen target resource maxima; actual actions stopped early on completion.
- Zero-shot, structural probing, accommodation, and regression were recorded separately.
- Blind games were generated once after validation selection was sealed; the canonical blind panel ran once.
- Independent cells used immutable inputs and coordinator-only writes. Serial and process candidate evaluation select the same action in integration tests.
- Probe information-value terms are audit-only because the algorithm freeze precedes the benchmark; they do not alter the existing deterministic disagreement policy.
- This benchmark is synthetic and makes no claim of official ARC or Kaggle competence.

Per-target, per-source, causal-matrix, selection, resource, failure-class, transported-diagram, and raw trace evidence is available in the adjacent canonical JSON/CSV artifacts.
