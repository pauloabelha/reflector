# Results

Status: **bounded public held-out screen complete; live intervention stopped by
the preregistered action-spending gate**.

The bundled synthetic fixture is only a deterministic mechanical test. Its
outputs are not ARC evidence and cannot justify promotion.

## Preregistered real-data screen

The split in `real-screen-split.json` was frozen before evaluating the held-out
trajectory. The learner saw 530 transitions from historical `sc25` and public
`lf52` recordings (523 neutral, 7 positive). The completely disjoint public
`r11l` recording supplied 393 held-out transitions (392 neutral, 1 positive),
with zero overlapping event IDs.

- learning digest:
  `77853cd346e5311d8e9db6eb78b35ac808cc770add683934e2ab17ba9f1fe601`
- held-out evidence digest:
  `61d6df9281e57a086be71bfada98cc470c52d04098174e01c0671bc02f16f242`
- frozen-arm commit: `f2e5d69b795fdd9a685e037579c675b554e0bdac`
- frozen-arm source check: 3/3 hashes matched
- offline deterministic replay: passed

The frozen learner contained three structurally promoted schemas. Two neutral
schemas were eligible for matching:

| Outcome | Support | Contradictions | Distinct contexts | Confidence |
| --- | ---: | ---: | ---: | ---: |
| neutral | 477 | 7 | 477 | 0.983539 |
| neutral | 46 | 0 | 46 | 0.979167 |
| positive | 7 | 477 | 7 | 0.016461 |

The positive schema formed from genuine prior successes and retained every
neutral occurrence of the same consequence as contradiction evidence. Its
confidence was therefore far below the frozen `2/3` eligibility threshold.

## Held-out result

| Learner | Coverage | Positive commitments | Positive precision | Accuracy | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| real | 393/393 | 0 | undefined | 392/393 | 0.25 |
| reward-label permutation | 393/393 | 0 | undefined | 392/393 | 0.25 |
| consequence-pairing permutation | 393/393 | 0 | undefined | 392/393 | 0.25 |

The sole held-out positive event matched an eligible neutral schema with 46
supports, no contradictions, and confidence `0.979167`; it was prospectively
classified neutral. The real learner was consequently indistinguishable from
both frozen null controls on precision and calibration. Correct neutral
classifications were transfer class 2 (a different binding of the same reusable
consequence schema); there were no successful positive transfers in classes 1,
2, or 3.

The real learner passed the provenance, chronology, frozen-arm, and deterministic
replay checks, but failed both preregistered null-comparison gates and produced
no eligible positive held-out commitment. Per `real-screen-split.json`, this
forbids spending the five-game live intervention cohort. No new public/Kaggle
actions were consumed.

Scientific verdict: **`CONTINUE-DIAGNOSTIC`**. The current consequence vocabulary
is too coarse to distinguish progress-bearing instances from common neutral
instances. That finding does not authorize adding successor features, roles,
game semantics, or consequence chains inside this experiment.
