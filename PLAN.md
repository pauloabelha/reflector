# Reflector persistent plan

Last updated: 2026-07-28

## End state

Evolve a purely symbolic, open-source ARC-AGI-3 agent until it scores
competitively on the actual Kaggle competition while preserving this invariant:

> Every accepted descendant is the same offline package used by local
> development, official public-game evaluation, replay, population evaluation,
> and Kaggle inference. No translation or manual policy rewrite is allowed.

The goal is not complete. A local public-development gain, a Kaggle smoke test,
or a synthetic validation result is progress—not proof of competitive hidden
generalization.

## Authoritative current state

- Branch: `main`
- Participant repository: `git@github.com:pauloabelha/reflector.git`
- Upstream starter remote: `https://github.com/arcprize/ARC-AGI-3-Agents.git`
- Last pushed commit: `9802d4a`
- Accepted candidate: `candidate-3332b36c8afa95aa`
- Accepted agent: Reflector v21
- Accepted frozen inference commit: `e7037b4`
- Accepted public-development report:
  `reports/official-public-evaluation-v21-cross-level-relations-400.json`
- Accepted score: `0.8359967619742551`
- Accepted coverage: 25/25 games, 10,000 actions
- Accepted completions: 5 levels across 4 games
- Kaggle public score: not submitted
- Kaggle private score: unavailable
- Canonical human-readable report: `REAL_GAMES_REPORT.md`
- Unrelated user work: `reflector/concept_validation.py` is untracked; do not
  modify, delete, or commit it unless the user explicitly brings it into scope.

## Why the accepted agent wins what it wins

| Mechanism | Causal real-game evidence |
| --- | --- |
| Epistemic state-graph exploration | v14 exact equal-budget control scored zero; enabled agent solved `r11l` L1 in 18 actions and `lf52` L1 in 34. |
| Failure-driven click-ontology accommodation | v18 preserved both v14 wins and added `tn36` L1 in 123 actions; unconditional multicolor grouping had regressed `r11l`. |
| Within-frame local relation induction | v20 preserved v18 and added `ft09` L1 in 4 actions by inducing same/different constraints from solved panels. |
| Cross-level relation retention | v21 preserved v20 and added `ft09` L2 in 7 actions on an overlapping layout with no solved example. |

## Active experiment: v22 schema conservation

Candidate: `candidate-cf53e44f38d28623`  
File: `candidates/v22-conserved-relation-schema-400.json`

Observed v21 failure:

- `ft09` level 3 contains four unsolved relation panels.
- v21 overwrote its proven `{0: same, 2: different}` relation merely because
  three or more panels were visible.
- The resulting inversion caused failure after the 400-action budget.

Hypothesis:

- Preserve an induced operative relation across novel layouts.
- Do not replace it solely because several unsolved panels are present.
- Require outcome contradiction before future accommodation.

Current evidence:

- Focused tests, Ruff, and mypy pass.
- On official `ft09`, v22 completed levels 1–3 with level action counts
  `[4, 7, 152]`.
- Level 3 is a new completion but inefficient versus the 23-action human
  baseline.
- The recorded trace shows eleven relation-directed actions followed by a
  long fallback; the final required macro-cell corrections were rediscovered
  much later.
- v22 is experimental and must not replace v21 until the accepted-win
  regression gate, full 25-game evaluation, and Kaggle checks pass.

## Next actions

1. Analyze the v22 `ft09` level-3 recording to derive why correct relational
   constraints are not exhausted efficiently.
2. Test a general constraint-coordination improvement; do not add game IDs,
   fixed coordinates, or fixed colors.
3. Prefer a v23 descendant that retains level 3 while materially reducing its
   152 actions.
4. Run the promotion gate on `ft09`, `r11l`, `tn36`, and `lf52`; all five
   accepted v21 completions must remain.
5. Run all tests, Ruff, and mypy.
6. Freeze the inference commit and execute all 25 official public games with
   400 actions each.
7. Export the exact candidate and run the network-disabled Kaggle smoke test.
8. Update `REAL_GAMES_REPORT.md`, `DECISIONS.md`, and this plan; commit and
   push only after promotion evidence is complete.
9. Prepare the first real Kaggle notebook submission as an explicit external
   action. Report its public score and submission status separately; private
   score remains unavailable until Kaggle exposes it.

## Promotion gates

A descendant is accepted only if all are true:

- it adds a real level or materially improves score/efficiency;
- no accepted game completion regresses;
- the official target result is deterministic on rerun;
- the full 25-game report has exact 25/25 coverage;
- source commit and report SHA-256 are recorded;
- all tests, Ruff, and mypy pass;
- the exact candidate exports without translation;
- network-disabled Kaggle smoke passes;
- the mechanism and falsifying comparison are documented;
- `REAL_GAMES_REPORT.md` distinguishes local and Kaggle scores.

## Useful commands

```bash
.venv/bin/pytest -q
.venv/bin/ruff check reflector tests
.venv/bin/mypy reflector

.venv/bin/reflector official-run ft09 r11l tn36 lf52 \
  --environments-dir /home/pauloabelha/arc-agi-3-public-games-2026/environment_files \
  --recordings-dir /tmp/reflector-target \
  --config candidates/<candidate>.json --no-recordings --lightweight

.venv/bin/reflector official-public-run \
  --environments-dir /home/pauloabelha/arc-agi-3-public-games-2026/environment_files \
  --recordings-dir /tmp/reflector-public \
  --output reports/<result>.json \
  --config candidates/<candidate>.json --no-recordings --lightweight

.venv/bin/reflector-kaggle export \
  --config candidates/<candidate>.json --output /tmp/reflector-kaggle-dist
.venv/bin/reflector-kaggle smoke-test \
  --config candidates/<candidate>.json
```
