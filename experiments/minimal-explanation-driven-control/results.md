# Results: Minimal Explanation-Driven Control

## Verdict

**CONTINUE-DIAGNOSTIC**

The implementation passes the mechanistic hypothesis and fails to provide
behavioral improvement.  R2 explanations form, project action-conditioned
consequences before intervention, disagree, settle through ordinary shadow
reification/refutation, update their support, and change opaque actions.  They
did not produce ARC progress in either the 30-action focused run or the fixed
25-game diagnostic.

Promotion is therefore not justified.  Rejection is also premature because
the experiment established the requested causal bridge and the public suite
was deliberately only five actions per game after full R2 composition proved
prohibitively expensive on longer heavy-game trajectories.

## Implementation outcome

The branch adds one episode-local `Explanation` scaffold.  It references
active transition schemas and current `Binding` records, constructs a stable
top-k beam (default 8), derives predictions from existing R2 `Change` and
`Preserve` atoms, and commits selected predictions as normal `Shadow` records.
The successor is represented with the normally learned R2 transition schema;
the same shadow machinery then reifies or positively refutes each commitment.

Learned transition schemas receive ordinary `supports` links from the bounded
predecessor binding frontier.  This makes them reachable from later active
frontiers without scanning dormant schemas.  Observation-driven shadows and
final-boundary action commitments have separate hard budgets (64 and 8 per
cycle respectively); both use the same records and reconciliation semantics.

The final controller supports three frozen policies:

- `random`: seeded uniform legal action;
- `local-schema`: active transition-schema support/progress/risk ranking;
- `explanation`: bounded assemblies plus support and effect-signature
  disagreement.

No game ID, level ID, coordinate, object role, action semantics, LLM, neural
policy, solver heuristic, or successor data enters explanation construction or
ranking.  Complex-action coordinates remain random samples made after the
opaque action ID is selected.

## Focused public-game trace

The 30-action `ar25` matched run produced:

| Metric | Result |
|---|---:|
| Explanations constructed | 25 |
| Prospective commitments | 50 |
| Reified shadows | 24 |
| Refuted shadows | 26 |
| Decisions whose top action changed | 23 |
| Disagreement-selected actions | 24 |
| Disagreement settlements | 24 |
| Progress/completed levels, all policies | 0 |

Decision 7 is a complete active-equilibration trace.  The seeded random top
was opaque action 6.  Two explanations predicted different consequences for
opaque action 3:

```text
E4 support=.50
  action 3 -> Change(Color), Preserve(EnclosureCount, Form, Kind)

E5 support=.67
  action 3 -> Preserve(Color, EnclosureCount, Form, Kind)

action 3 score=.0567
  predicted_progress=0
  discrimination=.40
  risk=.50
  support=.5833

selected: action 3 (changed from random action 6)
projected shadows: E4=#382, E5=#381

successor:
  observed schema = E5's preserve consequence
  E4 #382 REFUTED; score -> .14
  E5 #381 REIFIED; score -> .7867
  ambiguity 2 -> 1
  ARC progress delta = 0
```

This satisfies the required causal sequence, including a behavior-changing
choice and prospective settlement, but it is negative evidence for control:
the informative action did not advance the game.

## Fixed 25-game public cohort

Configuration:

- all 25 bundled public games;
- seed 0;
- five actions per policy/game (125 actions per policy);
- identical environment seed, action budget, perception, schema learner, and
  harness across policies;
- maximum eight explanations;
- game-isolated process workers;
- full `--workers 4` run followed by full `--workers 1` replay.

The deterministic game records were **exactly identical** between one and four
workers.

### Control result

| Policy | Score | Progress | Completed levels | Games with progress | Actions |
|---|---:|---:|---:|---:|---:|
| Random | 0 | 0 | 0 | 0 | 125 |
| Local schema | 0 | 0 | 0 | 0 | 125 |
| Explanation | 0 | 0 | 0 | 0 | 125 |

### Explanation result

| Metric | Result |
|---|---:|
| Explanations constructed | 91 |
| Mean / max active | 1.64 / 4 |
| Mean constituent count | 2.43 |
| Mean lifetime | 1.06 decisions |
| Changes / retirements | 59 / 16 |
| Commitments | 34 |
| Reified / refuted / abstained | 19 / 15 / 0 |
| Mean support at commitment | .7042 |
| Confirmation rate | .5588 |
| Decisions whose top action changed | 29 / 125 |
| Games with at least one changed action | 18 / 25 |
| Progress after changed actions | 0 |
| Regressions after changed actions | 0 |
| Level completions after changed actions | 0 |
| Action-changing precision | 0 |
| Decisions with no action prediction | 25 |
| Games with no explanation formed | 0 |

Action changes were not concentrated in one game: the largest game accounted
for 13.8% of changes.  No five-action suite decision selected an action partly
because of within-action explanation disagreement; the longer `ar25` run did
so 24 times.  This difference is expected from the short suite horizon: most
games had only one supported effect schema per action by decision five.

## Answers to the preregistered questions

1. **Did R2 explanations form on real games?** Yes.  They formed in all 25
   games; 91 were constructed in the fixed cohort.
2. **Did they make prospective intervention predictions?** Yes.  The cohort
   produced 34 pre-successor commitments; the longer trace produced 50.
3. **Did competing explanations disagree usefully?** Mechanistically yes in
   the longer trace: disagreement changed choices and was reduced by the
   successor.  Behaviorally no: it yielded no ARC progress.
4. **Did outcomes reweight/refute them prospectively?** Yes.  The cohort had
   19 reifications and 15 refutations; focused `ar25` had 24 and 26.
5. **Did the explanation layer change actions?** Yes: 29 cohort decisions
   across 18 games, and 23 of 30 focused `ar25` decisions.
6. **Did changed actions improve progress/completion?** No.  All progress,
   completion, score deltas, and action-changing precision were zero.
7. **What is the dominant bottleneck?** The learned morphisms predict local
   structural preservation/change, but R2 has no reliable generic bridge from
   those effects to ARC progress.  The controller therefore favors supported
   novelty or discrimination without knowing which structural changes matter.
   A secondary engineering bottleneck is the cost of full R2
   perception/composition on longer trajectories; explanation beam cost was
   not the dominant runtime.

## Interpretation

The central hypothesis splits cleanly:

- **Executable episode model:** supported.  Existing R2 schemas can be
  assembled into bounded prospective models and updated by intervention.
- **Improved action selection:** not supported by this experiment.  The
  explanation layer reliably changes behavior, but its effect vocabulary is
  not yet aligned with progress.

The next diagnostic should remain small.  It should test whether R2 can learn
a generic, prospectively calibrated relation between transition consequences
and legally observed progress/reward—without adding object roles, goals,
game-specific semantics, or rollout search.  Until that bridge exists, more
planning depth would amplify an ungrounded preference rather than solve the
measured bottleneck.

Machine-readable cohort evidence is in `suite-5/summary.json`.  Human-readable
per-decision and R2 traces are under `suite-5/runs/<game>/<policy>/traces/`.
The longer causal trace is under `runs/ar25/explanation/traces/`.
