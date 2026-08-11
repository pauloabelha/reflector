# Checkpoints

This file is append-only. A checkpoint is written at every phase boundary and
at least once per hour during active work.

## CP-000 — Experiment opened

- **Phase:** audit and freeze
- **Repository:** `/home/pauloabelha/reflector2`
- **Prior experiment:** `pcw-v1-16-qwen-executor-v0`, preserved unchanged
- **Authoritative insights:** `insights/kaggle/insights.md` and linked evidence
- **Verified:** prior A completed level 1 in 38 actions; prior B/C acted zero
  times; C emitted code but did not execute it; counterfactual directory empty
- **Frozen battlefield rule:** earliest qualifying history-bearing frozen A
  control decision; resolves to index 25 without consulting new B/C outputs
- **Worktree condition:** pre-existing modified and untracked files are present;
  this experiment writes only its new directory and new run artifacts
- **Current uncertainty:** whether the local 4B Executor can comply with the
  repaired contract and use history productively
- **Next step:** implement identity, proposal coherence, treatment compliance,
  checkpoint comparison, and verdict fixtures

## CP-001 — Causal substrate qualified

- **Phase:** causal protocol and battlefield preparation
- **Tests:** 11 qualification tests passed
- **Controls:** positive, negative, and inconclusive verdict fixtures passed;
  empty-history false claims rejected; no-trigger state routes deterministically
  to the sole Executor policy
- **Battlefield:** frozen `ar25` decision index 25, after 25 exact predecessor
  transitions
- **Observation:** `736bebcd334f7acb90a55330d486f20b30260907d4cb78a84b874bde44b0e17b`
- **Legal actions:** `[1, 2, 3, 4, 5, 7]`
- **Frozen A candidate:** action 2; stored separately and sealed from B/C
- **Snapshot:** full immutable packet approximately 4.19 MB; compact prompt view
  389,042 bytes; full packet remains available only to bounded C computation
- **Identity:** prefix, observation, source, config, seed, primitive, and snapshot
  hashes materialized in `artifacts/battlefield/battlefield.json`
- **Verified:** B/C receive existing PCW predictions as inputs but no baseline
  selection; no-trigger routing does not return action authority to R2
- **Current uncertainty:** whether model calls comply with the stricter proposal
  and code-provenance contract
- **Next step:** implement matched Executor calls, exact branch runner, and frozen
  evaluation assembly

## CP-002 — First model qualification attempt preserved

- **Phase:** matched worker qualification
- **Exact A replay:** passed before model calls
- **Context qualification:** initial 55.9 KB view produced 31.2k prompt tokens
  and was rejected before inference; repaired projection is 36.6 KB and 20.8k
  prompt tokens
- **B:** completed verbal analysis and proposal; selected action 1
- **C:** inference occurred, but the model exhausted its completion budget by
  repeating prose inside one code string; structured JSON was incomplete and no
  Python executed
- **Environment branches:** none for B/C
- **Verdict:** qualification failure, not a mechanism result
- **Preservation:** request, response, B proposal, C malformed response, and
  summary copied to `artifacts/qualification-attempts/pre-code-line-bounds/`
- **Repair:** freeze generic per-line and line-count limits; prohibit comments,
  functions, prints, and prose in code; require a short exact history query;
  rerun both matched arms
- **Next step:** regenerate manifest, rerun all controls, then rerun B/C

## CP-003 — Decisive matched attempt stopped at the causal gate

- **Phase:** matched run and finalization
- **Frozen manifest:**
  `2e0b8ece88e747c324ea7b006a55cd5ff2f25547d35e664f8d947997016483bc`
- **Exact A replay:** passed from the 25-transition prefix; action 2 reproduced
  the frozen successor digest
- **B:** verbal analysis completed, but proposal generation reached the context
  limit while filling an unbounded reason string; its JSON was incomplete
- **C:** Python mode was requested and code was emitted, but the code contained
  unterminated string literals; the sandbox rejected it before execution
- **Treatment compliance:** failed (`PYTHON_NOT_SUCCESSFUL`)
- **B/C environment branches:** zero; the arbiter/action gate remained closed
- **Physical actions spent by this attempt:** only the exact offline A replay;
  no treatment action was authorized
- **Verdict:** `INCONCLUSIVE / CAUSAL_PRECONDITION_FAILED`
- **Important artifact caveat:** arm directories contain attempt-level files
  from more than one qualification pass. `artifacts/SUMMARY.json`, per-arm
  `failure.json`, and the preserved qualification-attempt directory determine
  chronology; a future runner must use immutable run IDs rather than mutable
  arm directories
- **Next step:** freeze this v0 result. Treat bounded-output grammar and
  immutable run directories as preregistered infrastructure fixes before a new
  attempt; do not interpret this run as evidence for or against Python utility

## CP-004 — Interface qualification repair frozen

- **Phase:** resumed full-goal qualification
- **Reason for resumption:** the previous inconclusive attempt was a checkpoint,
  not the requested full eight-hour outcome
- **Scope:** unchanged A/B/C arms, battlefield, primitive set, model, authority
  funnel, and one-action branch protocol
- **Artifact isolation:** new matched attempts allocate immutable
  `artifacts/runs/run-NNN-<manifest>/` namespaces and publish `LATEST.json`
- **Grammar repair:** dependency membership moved from enormous JSON enums to
  strict host validation; every free-text action field is now length-bounded
- **C computation contract:** one bounded Python program, an exact documented
  `query_transitions` signature and valid generic example, no prose strings;
  proposal findings are derived from the executed return value rather than the
  model's pre-execution claim
- **Model packet:** 28,301 compact bytes, down from 36,612; full immutable
  snapshot hash remains
  `c4fa0da5963a839c0b1e9159a14afeabcb8faa0e474f1d4ebbc625a0b02633a8`
- **Tests:** 14 passed
- **Controls:** positive/negative/inconclusive verdicts, empty-history rejection,
  and sole-Executor no-trigger routing passed
- **Frozen manifest:**
  `f578e21b830adcd93eb40456c2d88878d77cbf5da207e0972e2c45705b038fc3`
- **Next step:** run a newly namespaced matched attempt

## CP-005 — Immutable run 001 diagnosed dependency-alias failure

- **Phase:** matched interface qualification
- **Attempt:** `run-001-f578e21b830a`
- **A replay:** exact
- **B/C:** both completed compact structured analysis, but cited conceptual
  names (`grid_encoding`, `transition_history`, `query_transitions`) where the
  contract requires provenance IDs
- **C code:** syntactically valid generic history-count program; not executed
  because dependency validation precedes computation
- **B/C branches:** zero
- **Diagnosis:** removing the enormous grammar enums also removed the model's
  explicit reference vocabulary. Host rejection was correct; the prompt did
  not state the replacement membership contract clearly enough
- **Repair:** include one compact `valid_dependency_ids` catalogue and require
  exact copying; retain strict host membership checks
- **Next step:** rerun both matched arms under a new manifest and namespace

## CP-006 — Immutable run 002 reached computation and proposal validation

- **Phase:** matched interface qualification
- **Attempt:** `run-002-f8c8b6185b1c`
- **A replay:** exact
- **B:** valid analysis and selected action 1, but candidate dependencies used
  the computation ID instead of workspace IDs
- **C:** valid analysis; bounded Python executed successfully over all 25
  transitions in 0.072 seconds and returned per-action counts; selected action 1
- **C provenance failure:** the proposal cited `finding:1`–`finding:5`, while
  the executed return is intentionally represented by the sole `finding:0`
- **B/C branches:** zero; proposal validation blocked both
- **Repair:** publish exact valid dependency IDs and executed-finding references
  at proposal time; dynamically restrict the finding grammar to the actual
  computation output count; validate abstention dependencies too
- **Next step:** rerun both arms from the unchanged battlefield

## CP-007 — Immutable run 003 is the first causally valid specimen

- **Phase:** decisive mechanism specimen before final evaluator completion
- **Attempt:** `run-003-2ed07ab25db9`
- **Exact branches:** A, B, and C all replayed from the identical decision-25
  prefix
- **Actions:** A selected 2; verbal B selected 1; Python C selected 1
- **C treatment:** engaged; one bounded program queried all 25 transitions and
  returned per-action counts; selected proposal cited the computation result
- **Immediate outcomes:** all arms had zero level progress, novelty 1, and no
  hard risk; B and C produced the identical successor digest
- **Checkpoints:** both conjunctions passed all five predicates; B confidence
  0.813 (Brier 0.034969), C confidence 0.084 (Brier 0.839056)
- **Frozen C>B verdict:** negative; Python did not change the action and sharply
  worsened calibration
- **Evaluator gap found:** B>A and C>A were described but not separately
  adjudicated by a frozen function
- **Next step:** add separate system-comparison verdicts and run live information
  controls before one final frozen attempt

## CP-008 — Model-in-the-loop controls completed with zero game actions

- **Phase:** negative controls
- **Manifest:**
  `68b7f0e357cdadf8782b785a4150ad1bdbc070d69e32cf6808d14d99e619ca62`
- **Environment actions:** zero
- **B action/effect permutation:** passed exactly; original action 1 mapped to
  action 2 under the coherent 1↔2 permutation
- **Dependency deletion:** both B and C later cited removed transition IDs;
  strict host validation rejected the proposals
- **C robustness:** original control failed analysis dependency validation;
  permuted control did not engage Python successfully
- **Control verdict:** failed overall, localized to provenance/tool robustness;
  not interpreted as gameplay evidence and not tuned away
- **Final evaluator:** 16 tests pass and emits distinct B>A, C>A, and C>B
  verdicts
- **Next step:** final matched run under the same manifest

## CP-009 — Canonical final run 005 frozen

- **Phase:** final matched evaluation
- **Attempt:** `run-005-d0073788d746`
- **Source manifest:**
  `d0073788d746a42c40d25351ae8ec363e5dd6c046b73d4d785eb49e7b2f5a2fc`
- **Exact replay:** A/B/C passed from observation
  `736bebcd334f7acb90a55330d486f20b30260907d4cb78a84b874bde44b0e17b`
- **Actions:** A=2, B=1, C=1
- **Treatments:** verbal B engaged; Python C engaged with successful execution
  and selected-proposal provenance
- **B>A:** negative, no target-outcome improvement
- **C>A:** negative, no target-outcome improvement
- **C>B:** negative, no code-mediated action change or target-outcome improvement
- **Checkpoints:** both passed all predicates; B Brier 0.034969, C Brier
  0.839056
- **Resources:** B 2 calls / 28,014 input / 3,122 output / 75.77 s; C
  2 calls / 28,296 input / 3,273 output / 79.26 s plus one 0.072 s Python call
- **Live controls under same manifest:** zero environment actions; B permutation
  equivariant; overall robustness control failed and is preserved
- **Final interpretation:** the narrow mechanism is executable and auditable,
  but neither the dedicated Executor nor bounded Python improved the
  preregistered one-step outcomes at this boundary

## CP-010 — Final R2 authority audit closed

- **Phase:** completion audit; no protocol or game-state mutation
- **Environment actions:** zero
- **Model calls:** zero
- **Experiment-local tests:** 16 passed
- **Inherited v0 authority/isolation tests:** 9 passed
- **Total executable checks:** 25 passed
- **Proved boundaries:** R2's action selector is never called in B/C; Executor
  is the sole concrete proposal source; Semantic and Executor contexts are
  logically isolated; Executor/code events cannot alter empirical support; the
  sandbox is fresh/read-only; one-action execution is replayable; primitives
  remain generic and game-semantic-free
- **Artifact:** `artifacts/controls/static-authority.json`
- **Conclusion:** the negative causal result is frozen with the intended R2
  authority, evidence, and action-cost boundaries intact
