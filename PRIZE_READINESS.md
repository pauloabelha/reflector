# ARC Prize 2026 readiness

Audit date: 2026-07-27. This is an engineering compliance review, not legal
advice. The binding source is the current
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

- Run the official agent on all 25 public environments after accepting the
  data rules and obtaining an ARC API key; report completion and RHAE, not
  only `bt11`. Anonymous API access currently returns HTTP 401.
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
