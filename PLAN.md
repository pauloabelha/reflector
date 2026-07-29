# Reflector persistent plan

Last updated: 2026-07-29

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
- Accepted candidate: `candidate-309548c858c10616`
- Accepted agent: Reflector v29
- Accepted frozen inference commit: `54db179`
- Accepted public-development report:
  `reports/official-isolated-public-v29-mature-causal-role-reuse-400.json`
- Accepted score: `2.9338884001495003`
- Accepted coverage: 25/25 games, 10,000 actions
- Accepted completions: 9 levels across 5 games
- Kaggle public score: not submitted
- Kaggle private score: unavailable
- Canonical human-readable report: `REAL_GAMES_REPORT.md`
- Maintenance state: canonical code is organized under `reflector/core/`,
  `reflector/runtime/`, `reflector/research/`, and `reflector/evolution/`.
  Legacy top-level imports remain compatibility aliases.

## Why the accepted agent wins what it wins

| Mechanism | Causal real-game evidence |
| --- | --- |
| Epistemic state-graph exploration | v14 exact equal-budget control scored zero; enabled agent solved `r11l` L1 in 18 actions and `lf52` L1 in 34. |
| Failure-driven click-ontology accommodation | v18 preserved both v14 wins and added `tn36` L1 in 123 actions; unconditional multicolor grouping had regressed `r11l`. |
| Within-frame local relation induction | v20 preserved v18 and added `ft09` L1 in 4 actions by inducing same/different constraints from solved panels. |
| Cross-level relation retention | v21 preserved v20 and added `ft09` L2 in 7 actions on an overlapping layout with no solved example. |
| Mature-stall causal role reuse | v29 preserved all eight v25 levels at exact action counts and added `lp85` L1 in 37 actions; the source-matched control remained at zero on `lp85`. |

## Accepted parent mechanism: v25 global relation constraints

Candidate: `candidate-036a55bfb6956008`

File: `candidates/v25-global-relation-constraints-400.json`

Hypothesis:

- Infer one coordinate-free tile lattice from observations.
- Coordinate overlapping clue constraints on that lattice and act only where
  all observed constraints agree that a block violates the learned relation.

Current evidence:

- Two official `ft09` runs exactly matched: five levels with level action
  counts `[4, 7, 14, 16, 94]`.
- The four-game gate preserved all accepted v21 completions and reached eight
  levels total.
- Every runtime action can now emit a bounded cognitive JSONL event containing
  advisor arbitration, transition evidence, and construction deltas. The LLM
  may inspect these traces between runs but is never called by the deployed
  policy.
- Full verification passes: 124 tests (3 skipped), Ruff, mypy, both packaged
  smoke paths, and exact-v25 export.
- Two paired process-isolated gates exactly reproduced: the source-matched
  ablation reached seven levels and v25 reached eight, preserving all prior
  completions.
- The strict isolated 25-game run scored 2.9104325118/100 with 8/183 levels
  and complete coverage. Its one-factor ablation scored 2.1693300953 with
  7/183. V25 is accepted.

## Accepted experiment: v29 mature-stall causal role reuse

Candidate: `candidate-309548c858c10616`

File: `candidates/v29-mature-causal-role-reuse-400.json`

Mechanism:

- after 32 interventions without level progress, reuse only roles with an
  observed rendered response;
- cap reuse at eight trials per level, then return to variation;
- suppress the advisor when a conserved learned relation is active.

Evidence:

- the watched five-game curriculum exposed that unbounded reuse solved
  `lp85` but regressed `ft09`;
- two exact six-game runs preserved all affected accepted action counts and
  added `lp85` L1 in 37 actions;
- the full source-matched v25 genome reproduced 8/183 and
  `2.9104325118287466/100`;
- the full v29 candidate preserved those eight levels exactly, added `lp85`,
  and reached 9/183 and `2.9338884001495003/100`;
- 148 tests passed (3 skipped), Ruff and mypy passed, both network-disabled
  smoke paths passed, and the exact genome exported without translation.

V29 is accepted.

## Rejected experimental branch: v28 object and temporal primitives

V28 implemented content-free persistent components, composite regions,
enclosures, normalized shape forms, connected frame differences, discrete
object flow, and primitive-grounded intervention provenance. The full
offspring added `lp85` and `sp80`, but lost `tn36` and slowed `lf52` and
`r11l`, scoring `2.8820272500/100`. The ontology remains behind exact-off
genome flags, but none of its active policy traits are inherited by v29.

## Completed experimental branch: v26

- Preregistered causal hypotheses and typed predictive/pragmatic structural
  credit are implemented.
- Successful procedures are first-class scheme inputs with bounded prefix,
  suffix, interleaving, and role-binding variation.
- Pragmatic stagnation triggers variation; composite applications receive
  component-specific falsification.
- The full v26d run preserved eight levels and increased score slightly, but
  the gain came only from successful role replay. V26e and v26f improved
  trace-level inhibition without task gain. None is promoted.

## Next actions

1. Inspect `lp85` level 2 plus the zero-progress `ar25`, `g50t`, and `sb26`
   streams. Prioritize ordered/cyclic comparison, controllable-object
   attribution, topology, and delayed select-then-confirm composition.
2. Route qualitative frame difference and flow into causal policy only through
   typed, bounded advisors; passive perception alone is not task credit.
3. Evaluate diverse operators in isolated populations across games; require a
   new level or material efficiency gain from each operative trait.
4. Run source-matched target ablations and the full 25-game gate only for a
   qualifying offspring; keep v29 accepted otherwise.
5. Prepare the first real Kaggle notebook submission as an explicit external
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
