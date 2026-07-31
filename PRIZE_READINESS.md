# ARC Prize 2026 readiness

Engineering audit updated: 2026-07-31. The machine-readable rules snapshot is
dated 2026-07-27 and remains within its 14-day freshness gate. This is an
engineering compliance review, not legal advice. The binding source is the
current
[Kaggle competition rules](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules);
the host may change dates or requirements.

## Recommended track strategy

Reflector should enter the ARC-AGI-3 code competition and link that working
entry to the 2026 Paper Prize.

The Paper Prize is the strongest current fit. It explicitly says the linked
Kaggle entry need not score highly, while evaluating accuracy, universality,
progress, theory, completeness, and novelty equally. Reflector already has a
distinct symbolic thesis, an operative implementation, deterministic traces,
ablation machinery, and explicit approximations. It does **not** yet have
enough multi-game evidence for a prize-quality paper.

The current accepted v99k public-development result is
`21.632592714022195/100`: 51/183 levels across 15/25 games, with `sb26`,
`ft09`, and `cd82` fully completed. This is materially stronger than fixture-only
compatibility but remains known-public development evidence, not a Kaggle
leaderboard result or a competitive hidden-game claim.

The same entry is formally eligible for these ARC-AGI-3 awards if it places:

- Milestone 2 top three, with a public open-source notebook by September 30;
- final private-leaderboard top five;
- the 100% bonus pool, if it reaches 100%.

Those score tracks are valid but currently aspirational. A perfect `bt11`
fixture run is a compatibility result, not evidence of competitive performance
on the 110 unseen evaluation games.

## Binding competition envelope

| Requirement | Current value | Reflector status |
| --- | --- | --- |
| Entry safety cutoff | October 26, 2026, 11:59 UTC | Manual |
| Team merger deadline | October 26, 2026, 23:59 UTC | Manual |
| Final submission | November 2, 2026, 23:59 UTC | Manual |
| Paper safety deadline | November 8, 2026, 23:59 UTC | Manual |
| Binding Paper Track deadline | November 9, 2026, 23:59 UTC | Manual |
| Team size | At most 8 | Manual |
| Daily submissions | 1 | Process rule |
| Final selections | At most 2 | Process rule |
| Notebook runtime | CPU/GPU at most 9 hours | Pass locally; Kaggle rerun required |
| Internet | Disabled | Pass in artifact and smoke test |
| Submission | Notebook; automatic `submission.parquet` | Pass |
| Artifact limit | 20,480 MB | Pass |
| Evaluation | 110 hidden games, 50/50 public/private split | Kaggle only |
| Winner source grant | CC BY 4.0 | Covered for Reflector contributions |
| Open system/model/parameters | OSI checklist | Pass; no neural weights exist |
| Competition data | Apache 2.0; security duties apply | Documented |

The machine-readable snapshot is
[`competition/arc_agi_3_2026.json`](competition/arc_agi_3_2026.json); the
separate Paper Track snapshot is
[`competition/arc_prize_2026_paper.json`](competition/arc_prize_2026_paper.json).
The ARC Prize summary and Kaggle disagree by one day on the paper deadline, so
Reflector uses November 8 as its safety deadline.

## Technical compliance

Reflector:

- preserves `is_done` and `choose_action` and the official `Swarm` lifecycle;
- uses only the local competition gateway during a rerun;
- writes only under `/kaggle/working`;
- installs dependencies only from the attached competition wheels;
- never contacts `three.arcprize.org` or an external LLM during evaluation;
- embeds the exact inference overlay and selected symbolic genome;
- contains no Kaggle-path database, web server, model download, or remote API;
- emits only actions reported legal by the latest observation;
- has a permanent network-disabled packaged smoke test;
- separates third-party MIT starter code from dual-licensed contributions;
- discloses that the symbolic model has parameters but no weights.

The accepted inference package is frozen at source commit `794d9a1` and
candidate commit `38cb243`, candidate `candidate-ddf2529a2bae5601`. Its exact 25-game
scorecard has complete 25/25
coverage; its target repeats, 15-game preservation gate, full suite,
pytest, Ruff, mypy, direct export, both network-disabled smoke paths, and
technical prize audit pass. Exact current artifact hashes are:

- candidate:
  `fa2c05667cca8078123d0e517f7918a9a701a8e1dfa9d6dfb35e0332d92bbc58`;
- Kaggle overlay:
  `0b27853b2e428f0a8aee6219b7cf90f2c8d559f5ff435e3b32c591e9d5eefbef`;
- Kaggle notebook:
  `dd93c904b2a44ee7ba53a6e591c51cfd64e0e595bb27751a596a063edf3a3143`;
- accepted 25-game report:
  `8160783c9aae6c62fda71a8338e118c730debf3f1b76b79ecec7d494b1e7c74a`.

`technical_ready` is true. `prize_ready` remains false because the account,
publication, and committed Kaggle-rerun gates below are manual.

The exact private v94b notebook version 1 has completed and emitted
`submission.parquet`. Its competition submission request returned HTTP 400
while pending v74 submission `55123277` occupies the daily allowance; no v94b
submission ID exists yet.

The exact private v97 notebook version 1 has also completed and emitted
`submission.parquet`. Its competition submission request returned HTTP 400
under the same pending-v74 quota condition; no v97 submission ID exists.

The exact private v98 notebook version 1 completed and emitted a 2,648-byte
`submission.parquet`. Its competition request returned HTTP 400 because v74
had consumed the UTC daily allowance; no v98 submission ID exists. V74
submission `55123277` subsequently completed at public score `0.02`, matching
v65b `55113224`. The v98 version must be submitted unchanged after the quota
resets.

## Required account and publication actions

These cannot be completed from a local checkout:

1. Re-authenticate GitHub and create a public repository owned by the
   participant or team. The current `origin` still points to the ARC Prize
   starter and is not a publication location for Reflector.
2. Accept the Kaggle rules before the entry cutoff, complete identity
   verification, and confirm age, jurisdiction, sanctions, employer, and tax
   eligibility.
3. Do not privately share competition code outside the registered Kaggle team.
   Public sharing must also be posted through the competition forum or a
   competition notebook.
4. Import `dist/reflector-kaggle-submission.ipynb`, attach the official
   competition data, explicitly disable internet, select the intended CPU or
   GPU, and commit a full run.
5. Confirm that the committed rerun receives a score. Make the exact notebook
   and complete public repository available before receiving private
   evaluation results or claiming a prize.
6. Archive the source commit, candidate JSON, notebook version, overlay hash,
   lockfiles, runtime resources, scorecard, and public-game evaluation report.
7. Keep the Paper Track team exactly identical to the linked ARC-AGI-3 team.
   Submit its only allowed Writeup—not a draft—with at most 1,500 words, a
   selected track, cover image/media gallery, public notebook, and code
   submission ID. A public project/PDF link is optional.
8. Publish the Paper Prize submission only after reporting held-out public
   evaluation results—not training/fixture performance—and link the real
   Kaggle code submission.

## Research gates before a credible paper

- Preserve the completed 25-game public evaluation as the known-public
  development baseline: 25/25 coverage, 28/183 levels, 2/25 games complete,
  9,486 actions, and `9.684019526667843/100`. Do not relabel it as held-out or
  leaderboard evidence.
- Record completed v65b Kaggle submission `55113224` and public score `0.02`,
  monitor pending v74 submission `55123277`, then
  submit v68 only as a separately identified exact notebook/candidate. Never
  attribute a returned v65b score to v68.
- Replace transformed-trace “holdouts” with held-out environments for the main
  generalization claim.
- Compare the symbolic system against random, rare-color, schema-disabled,
  planning-disabled, abstraction-disabled, and score-only baselines.
- Demonstrate at least one cross-level or cross-game transfer result where an
  accepted abstraction changes action efficiency.
- Report failures and action budgets by game. Do not interpret internal schema
  reuse as external task generalization.
- Produce the short paper around the official rubric: clear theory,
  algorithm-level completeness, novel contribution, honest accuracy, and
  reusable evidence.

Run the repeatable local audit with:

```bash
.venv/bin/reflector-prize-audit
```

The audit fails its technical gate once the rules snapshot is more than 14
days old. Re-read the rendered Kaggle rules, overview, data page, current host
announcements, and Paper Prize page before updating the snapshot.
