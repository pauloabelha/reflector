# ARC-AGI-3 Kaggle submission runbook

Verified: 2026-07-30.

This is the operational runbook for submitting Reflector to
[ARC Prize 2026 - ARC-AGI-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3).
The binding source is always the current Kaggle competition page and rules.
Refresh the local rules snapshot and rerun the prize audit before every
submission.

## Decision

Submit Reflector after the exact v84m source, candidate, and permanent local
reports have been frozen and verified. A Kaggle submission is valuable because
it tests transfer to hidden games; the score on the 25 downloadable
public-development games cannot answer that question.

Do not spend the one-per-day submission allowance on a dirty worktree, a
candidate whose inference fingerprint does not match the source, or an export
that predates the accepted source commit.

## Keep the three score regimes separate

| Evidence | Games | When available | What it supports |
| --- | ---: | --- | --- |
| Local official public-development report | 25 downloadable games | Before submission | Regression, attribution, and packaging evidence on known games only |
| Kaggle public-leaderboard score | 55 hidden games, half of the 110-game evaluation | After a scored Kaggle rerun | Hidden-transfer calibration and public ranking |
| Kaggle private-leaderboard score | Remaining 55 hidden games | Final evaluation/verification | Final competition standing |

Never infer either Kaggle score from a local report. Submission `55113224`
contains frozen v65b and completed with public score **0.02**. Submission
`55123277` contains v74 and is pending. The completed v84m notebook version 1
has no competition submission ID because the v74 submission consumed the
daily allowance. Until Kaggle releases or verifies a final result, record the
private score as **unavailable**.

`REAL_GAMES_REPORT.md` is the canonical root-level score report. Raw local
scorecards belong under `reports/`. A target-only report and a report generated
from an unfrozen or dirty source tree are experimental evidence, not an
accepted local public-development score.

## Confirmed competition envelope

Kaggle's live metadata currently reports
`onlyAllowKernelSubmissions: true` and `usesSynchronousReruns: true`.
Consequently, a submission must identify a committed Kaggle notebook version
and its output file. Uploading a locally generated `submission.parquet` alone
is not a valid ARC-AGI-3 submission.

| Requirement | Current value |
| --- | --- |
| Submission type | Kaggle notebook version only |
| Required output | `submission.parquet` |
| Internet | Disabled |
| CPU runtime | At most 540 minutes |
| GPU runtime | At most 540 minutes |
| Submission artifact limit | 20,480 MB |
| Daily submissions | 1 per team |
| Final selections | Up to 2 |
| Team size | Up to 8 |
| Hidden evaluation | 110 games; 50% public leaderboard, 50% private leaderboard |
| Public-development data | 25 downloadable games |
| Identity verification | Required |
| Competition-data license | Apache-2.0 |
| Winner grant | CC-BY-4.0 |

Freely and publicly available external data and pretrained models are allowed,
subject to the rules. Reflector does not require them. Kaggle also exposes RTX
Pro 6000 machines specifically for ARC-AGI-3, but the symbolic candidate
should use CPU unless profiling demonstrates a real need for an accelerator.

### Dates

| Event | Deadline, UTC |
| --- | --- |
| Milestone 2 and public open-source notebook | 2026-09-30 23:59 |
| Entry safety cutoff | 2026-10-26 11:59 |
| Team merger | 2026-10-26 23:59 |
| Kaggle notebook-publishing cutoff in live metadata | 2026-10-26 23:59 |
| Final submission | 2026-11-02 23:59 |
| Results announcement | 2026-12-04 |

The rendered Kaggle timeline describes the entry deadline as October 26 at
23:59 UTC, while the live metadata reports 11:59 UTC. Use the earlier time and
join well before that date. Rules and dates can change.

Primary sources:

- [Kaggle ARC-AGI-3 rules](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules)
- [Kaggle ARC-AGI-3 data and evaluation description](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data)
- [Kaggle live competition metadata](https://www.kaggle.com/api/i/competitions.CompetitionService/GetCompetition?competitionName=arc-prize-2026-arc-agi-3)
- [Kaggle live competition pages](https://www.kaggle.com/api/i/competitions.PageService/ListPages?competitionId=133468)
- [ARC Prize ARC-AGI-3 requirements](https://arcprize.org/competitions/2026/arc-agi-3)
- [ARC Prize 2026 open-source rules](https://arcprize.org/competitions/2026)

## Freeze and verify the exact Reflector candidate

The current intended candidate is:

```text
candidates/v84m-grouped-dihedral-analogy-400.json
```

Its frozen identity is `candidate-07d24ee8acf946c9`, generation 47, parent
`candidate-5f09e48c374d0a52`, with inference fingerprint
`53729246c43ad6aadcc4fa4ba95a08510f0b200c83d08bd9ea3518816803e36d`.

First confirm that the implementation and candidate are in one frozen source
commit and that the worktree contains no uncommitted inference-path changes:

```bash
git status --short
git rev-parse HEAD
git show 59daf6171026b986c1e26aaa5fa1f56e2ef03269:candidates/v68-path-cycle-transport-400.json
```

The permanent target, preservation, and full 25-game reports must all name that
same source commit. Confirm that the candidate's recorded
`inference_fingerprint` equals the fingerprint computed from the frozen
inference closure. Do not reuse reports made before the source commit was
frozen.

Run the local quality and exact-candidate gates:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check reflector tests
.venv/bin/mypy reflector

.venv/bin/reflector-kaggle smoke-test \
  --config candidates/v84m-grouped-dihedral-analogy-400.json

.venv/bin/reflector-kaggle export \
  --config candidates/v84m-grouped-dihedral-analogy-400.json \
  --output dist

.venv/bin/kaggle_smoke_test
.venv/bin/reflector-prize-audit
```

The export must produce:

```text
dist/reflector-kaggle-overlay.zip
dist/reflector-kaggle-submission.ipynb
```

The notebook embeds both the exact inference overlay and the serialized v84m
`MindConfig`; it is the artifact to upload. The ZIP is an auditable copy of the
inference overlay and does not need to be attached as a separate Kaggle
dataset.

Record the final artifact hashes only after the last export:

```bash
sha256sum \
  candidates/v68-path-cycle-transport-400.json \
  dist/reflector-kaggle-overlay.zip \
  dist/reflector-kaggle-submission.ipynb
```

The verified 2026-07-30 hashes are:

```text
6e7bd19eecbaccfa670dca7b92c4cac3cf2dc1737fe6dd59724600e216e54fb4  candidate
7e2bce6fc750d8343b223e732fae75a91be79b4be93dc0d828714d59657bb731  overlay
c266c5e3e35e37312aa001ce28428e1c42fdbe539ab3f0b453ee6c120f9f099d  notebook
```

The accepted local public-development result bound to that inference source is
`20.561797304445623/100`, 48/183 levels, 3/25 complete games, and 25/25
coverage. It is not a Kaggle score.

## Browser submission workflow

The browser path is the preferred first-submission path because it makes the
competition source, internet setting, committed version, and output visible
before the one allowed daily submission is consumed.

1. Sign in to Kaggle, join the competition, accept the current rules, and
   complete identity verification.
2. Confirm the intended Kaggle team before submitting. Do not privately share
   competition code outside that registered team.
3. Open the competition's **Code** page and create a notebook, or upload
   `dist/reflector-kaggle-submission.ipynb`.
4. Attach the competition source
   `arc-prize-2026-arc-agi-3`. If the notebook was created from the competition
   page, verify that the source is already present rather than assuming it.
5. In notebook settings, set **Internet off** and select **CPU**.
6. Verify that the notebook source and visible embedded candidate correspond
   to the frozen source commit and final artifact hashes.
7. Choose **Save Version**, then **Save & Run All (Commit)**.
8. Wait for the committed version to complete successfully. Inspect its logs
   and confirm that `submission.parquet` is available as an output.
9. From that completed version/output, choose **Submit to Competition**, select
   `submission.parquet`, and use a message containing the Reflector version,
   candidate ID, and short source commit.
10. Capture the notebook slug and version plus the numeric submission ID. Wait
    for the competition rerun and scoring to finish, then record the returned
    Kaggle public score.

The notebook's ordinary commit establishes an eligible version and output.
Kaggle then performs a separate synchronous competition rerun against its
hidden gateway. Only the leaderboard result returned by that rerun is Kaggle
score evidence.

Kaggle occasionally changes UI labels. The invariant is: a successful
internet-disabled committed notebook version, the attached competition source,
and a submission referencing that version's `submission.parquet`.

## Optional Kaggle CLI workflow

The official CLI supports code-competition submissions, but it still submits a
specific Kaggle notebook version; it does not bypass the notebook requirement.

Create a staging directory containing the exported notebook and a
`kernel-metadata.json` like:

```json
{
  "id": "<kaggle-username>/reflector-arc-agi-3",
  "title": "Reflector ARC-AGI-3",
  "code_file": "reflector-kaggle-submission.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": "true",
  "enable_gpu": "false",
  "enable_internet": "false",
  "machine_shape": "",
  "dataset_sources": [],
  "competition_sources": [
    "arc-prize-2026-arc-agi-3"
  ],
  "kernel_sources": [],
  "model_sources": []
}
```

Authenticate, upload, and let Kaggle run the notebook:

```bash
kaggle auth login
kaggle kernels push -p <staging-directory>
kaggle kernels status <kaggle-username>/reflector-arc-agi-3
```

After the run succeeds, capture its numeric notebook version and submit that
exact version:

```bash
kaggle competitions submit arc-prize-2026-arc-agi-3 \
  -k <kaggle-username>/reflector-arc-agi-3 \
  -v <successful-notebook-version> \
  -f submission.parquet \
  -m "Reflector <candidate-id> <source-commit>"
```

The command returns a numeric submission reference. Poll that reference rather
than assuming that upload success means evaluation success:

```bash
kaggle competitions submission <numeric-submission-reference>
kaggle competitions submissions arc-prize-2026-arc-agi-3
```

Official CLI references:

- [Code-competition submission tutorial](https://github.com/Kaggle/kaggle-cli/blob/main/docs/tutorials.md#tutorial-how-to-submit-to-a-code-competition)
- [Notebook metadata format](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md)
- [Competition submission command](https://github.com/Kaggle/kaggle-cli/blob/main/docs/competitions.md#kaggle-competitions-submit)

## Evidence to archive

Before upload:

- source commit and clean-worktree confirmation;
- candidate path, candidate ID, parent ID, generation, mutation source, and
  `inference_fingerprint`;
- SHA-256 of the candidate JSON, overlay ZIP, and notebook;
- exact pytest, Ruff, mypy, exact-candidate smoke, generic network-disabled
  smoke, export, and prize-audit results;
- permanent target, preservation, and full 25-game report paths and SHA-256
  values;
- each local report's `source_commit`, coverage, score, completed
  games/levels, action counts, and comparison with its accepted parent.

At Kaggle:

- Kaggle account and exact team roster;
- notebook URL/slug, numeric version, visibility, license, competition source,
  accelerator, internet setting, start/end time, runtime, and commit status;
- notebook output listing and `submission.parquet` presence;
- submission message, numeric submission ID, submission time, status, and any
  rerun/error logs;
- returned Kaggle public score, explicitly labeled as hidden-public evidence;
- Kaggle private score as **unavailable** until it is actually returned;
- public notebook URL, participant-owned public repository URL, and the exact
  repository commit matching the submitted notebook.

After scoring, update `REAL_GAMES_REPORT.md` and `PLAN.md` in the same change.
Do not overwrite the local public-development score with the Kaggle public
score; record both on separate labeled lines.

## Open-source and prize requirements

For Milestone 2 eligibility, the notebook must be public under an open-source
license by September 30. ARC Prize also requires reproducible open-source
solutions before official private evaluation scores are received. Publish the
exact submitted notebook and complete implementation, not a similar or later
rewrite.

The competition rules require open-source system, model, and
weights/parameters under the Open Source AI checklist. Reflector has no neural
weights, but its symbolic parameters and absence of weights still need to be
disclosed. Winning submissions and the source that generated them are subject
to the specified CC-BY-4.0 grant. Public sharing of competition code must also
be made available through the competition's Kaggle notebook or forum, and
private code sharing outside the registered team is prohibited.

## Current manual blockers

At the 2026-07-30 audit:

- v84m is frozen as `candidate-07d24ee8acf946c9`; its candidate fingerprint,
  target repeats, preservation gate, full 25-game report, exact export, both
  network-disabled smoke paths, and technical prize checks pass;
- frozen v65b submission `55113224` is complete at Kaggle public score 0.02;
  v74 submission `55123277` is pending;
- v84m notebook `pauloabelha/reflector-arc-agi-3-v84m` version 1 completed and
  emitted `submission.parquet`, but the submission request was rejected after
  v74 consumed the daily allowance; no v84m submission ID exists yet;
- the project virtual environment has a working authenticated Kaggle CLI; a
  live read-only check reports `55113224` complete and `55123277` pending;
- rule acceptance, identity verification, eligibility confirmation, team
  selection, notebook upload, competition-source attachment, internet-off
  setting, committed rerun, and submission all require participant account
  actions;
- the participant-owned `reflector` Git remote exists, but the prize audit
  still sees the upstream ARC starter as `origin`; the exact submitted commit
  must be pushed to a participant-owned repository and confirmed publicly
  readable;
- the exact Kaggle notebook and public repository still need to be published
  through the competition before private scoring or prize review.

The repeatable audit currently distinguishes technical readiness from these
manual gates:

```bash
.venv/bin/reflector-prize-audit --json
```
