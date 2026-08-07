# Grand all-level transfer experiment

> Retrospective exploratory evidence over every compatible local level; not a blind or official Kaggle score.

- Levels: 84
- Directed cells: 7056
- Completion: 95.7%
- Zero-shot: 38.1%
- Mean transfer score: 0.5380
- Invalid cells: 84
- Regressions: 0

Validity note: all 84 invalid cells share source G076, whose developmental
exploration did not solve the motion-based genuine-novelty source within its
fixed budget. Among 6,972 valid cells, 6,752 solve: 96.84% completion, 38.51%
zero-shot, and 0.5445 mean transfer score. Raw and valid-only rates are kept
separate because source-learning failure is not a target-transfer failure.

## Solution phases

- accommodation: 2100 (29.8%)
- invalid: 84 (1.2%)
- none: 220 (3.1%)
- structural_probing: 1967 (27.9%)
- zero_shot: 2685 (38.1%)

## Variance decomposition

- Learned source: 18.6%
- Target difficulty: 37.4%
- Source-target interaction: 44.0%

## Corpus-to-corpus transfer

| Source | Target | Cells | Completion | Zero-shot | Transfer | Actions |
|---|---|---:|---:|---:|---:|---:|
| transfer-atlas | transfer-atlas | 400 | 99.5% | 33.8% | 0.5640 | 3.93 |
| transfer-atlas | v2-frozen | 640 | 98.6% | 44.5% | 0.5695 | 4.05 |
| transfer-atlas | v3-clean | 640 | 95.3% | 40.6% | 0.5616 | 4.34 |
| v2-frozen | transfer-atlas | 640 | 98.4% | 38.3% | 0.5901 | 3.97 |
| v2-frozen | v2-frozen | 1024 | 97.7% | 48.1% | 0.5977 | 4.09 |
| v2-frozen | v3-clean | 1024 | 94.7% | 42.0% | 0.5680 | 4.29 |
| v3-clean | transfer-atlas | 640 | 94.5% | 24.8% | 0.4430 | 4.42 |
| v3-clean | v2-frozen | 1024 | 94.2% | 33.9% | 0.4823 | 4.40 |
| v3-clean | v3-clean | 1024 | 92.1% | 32.3% | 0.4864 | 4.47 |

## Strongest learned sources

- G015: transfer 0.7981, zero-shot 63.1%, completion 98.8%
- G010: transfer 0.7879, zero-shot 63.1%, completion 97.6%
- G056: transfer 0.7875, zero-shot 63.1%, completion 95.2%
- G005: transfer 0.7780, zero-shot 63.1%, completion 96.4%
- G024: transfer 0.7757, zero-shot 63.1%, completion 96.4%
- G043: transfer 0.7714, zero-shot 63.1%, completion 97.6%
- G045: transfer 0.7706, zero-shot 63.1%, completion 97.6%
- G040: transfer 0.7704, zero-shot 63.1%, completion 96.4%
- G061: transfer 0.7683, zero-shot 63.1%, completion 97.6%
- G049: transfer 0.7680, zero-shot 63.1%, completion 96.4%

## Hardest targets

- G032: transfer 0.0111, completion 85.7%, actions 10.49
- G076: transfer 0.0192, completion 95.2%, actions 8.05
- G074: transfer 0.0222, completion 91.7%, actions 6.70
- G028: transfer 0.0232, completion 92.9%, actions 6.39
- G008: transfer 0.0242, completion 98.8%, actions 6.17
- G050: transfer 0.0318, completion 89.3%, actions 7.37
- G064: transfer 0.0436, completion 64.3%, actions 8.89
- G044: transfer 0.0651, completion 96.4%, actions 5.96
- G060: transfer 0.0882, completion 64.3%, actions 9.25
- G042: transfer 0.1620, completion 98.8%, actions 6.06

Full 84x84 completion, zero-shot, efficiency, and transfer matrices are in JSON and CSV artifacts.
