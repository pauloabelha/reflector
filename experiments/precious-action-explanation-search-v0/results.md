# Precious Action Explanation Search v0 — results

## Verdict

The intended mechanism was successfully engaged, but the result is **negative**
on this preregistered `ar25` decision boundary.

```text
B > A: no demonstrated benefit
C > A: no demonstrated benefit
C > B: no code-mediated benefit
```

The verbal and Python Executors both replaced frozen A's action 2 with action 1.
Neither changed immediate level progress, generic information novelty, or hard
risk relative to A. Python C chose the same action and exact successor as verbal
B, while making a much less calibrated forecast.

This is one development-game, one-boundary mechanism specimen. It is not a
leaderboard, transfer, or model-family claim.

## Repository understanding

The root `README.md` defines Reflector-II as an action-semantic-free symbolic
runtime whose proven main solver is exact frozen Parallel Cognitive Workspace
v1.16. `docs/ARCHITECTURE.md` makes the key boundaries explicit: the ledger and
epistemic graph are authoritative; Qwen state is a cache; only
environment-authored evidence changes support; the arbiter alone commits an
action; and the proven solver uses one serialized Qwen queue.

The relevant insight corpus supplies three complementary precedents:

- Duck: ephemeral bounded Python over compact observations/history, but an
  unsafe live-action callback;
- Schema: complete-history executable tests, internal search, guarded commit,
  and aggressive invalidation on prediction mismatch;
- PRO-LONG: large gains from programmatic access to exact persistent history,
  but weaker evidence/action distinctions and open-loop execution.

This experiment takes only their narrow intersection with R2: immutable
history, ephemeral generic computation, a typed proposal, one primitive branch,
and environment-settled prediction. It does not add a world model, planner,
skills, open-loop queue, game semantics, or a new ARC helper library.

The frozen baseline is the exact v1.16 `ar25` artifact that completed level 1 in
38 actions while R2-only completed zero levels in 64. The older Kaggle score
`0.02` is not attributed to v1.16.

## Protocol

- Game/version: `ar25-0c556536`
- Frozen source commit: `3da145b8d0f502c393d3fd9c6dc7d4a2d53d68ca`
- Seed: `314159`
- Battlefield: earliest qualifying frozen decision, index 25 after 25 exact
  predecessor transitions
- Pre-action observation:
  `736bebcd334f7acb90a55330d486f20b30260907d4cb78a84b874bde44b0e17b`
- Full snapshot:
  `c4fa0da5963a839c0b1e9159a14afeabcb8faa0e474f1d4ebbc625a0b02633a8`
- Primitive set: `executor-generic-primitives-v0.1`, source hash
  `2950ff439a59f80567d27ed3d2ac1710c5b25a8de010c6e5a8022e53583a934d`
- Legal opaque actions: `[1, 2, 3, 4, 5, 7]`

A's action 2 is stored separately and sealed from B/C. The sole B/C policy path
always reaches QwenExecutor when a legal action exists. B and C use separate
logical context/provenance names over one physical serialized Qwen server. Each
request is a complete stateless packet, so there is no shared hidden chat state.

C receives the same compact model packet as B and read-only computational access
to the full snapshot. Its subprocess has no network, environment callback,
filesystem capability, inherited environment, import, or empirical-write path.
The arbiter validates legality, provenance, dependency membership, treatment,
checkpoint executability, and exact prefix identity before any branch.

## First valid causal chain

The first valid specimen was immutable run 003; the final evaluator later
replicated it. Its chain was:

```text
25 exact environment transitions
-> deterministic decision-25 boundary
-> identical B/C snapshot
-> isolated Executor analyses
-> C query_transitions() over all 25 records
-> successful structured Python return
-> ranked B/C proposals
-> B action 1; C action 1
-> arbiter validates each independently
-> one exact action-1 branch per arm
-> identical successor digest
-> typed checkpoints settled from environment observations
```

C's code counted transitions per opaque action. It returned counts
`{1:6, 2:5, 3:4, 4:4, 5:3, 7:3}`. Its additional effect-pattern string was
hard-coded inside the generated program rather than derived, so only the counts
are credited as genuine code computation. The selected C candidate cited the
durable computation ID and its host-recorded result.

## Same-state counterfactual

| Arm | Action | Successor | Progress | Novelty | Hard risk | Residual |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| A | 2 | `55a5fe…9de5` | 0 | 1 | false | 72 |
| B | 1 | `315012…1827` | 0 | 1 | false | 84 |
| C | 1 | `315012…1827` | 0 | 1 | false | 84 |

All branches started from the same verified digest. B/C changed the frozen
action, but no preregistered target outcome improved. The lower A residual is
reported descriptively; it was not promoted post hoc into the verdict.

## Checkpoint calibration

Both B and C correctly predicted grid change, the changed-cell interval, zero
level delta, and nonterminal state. All five predicates passed.

| Arm | Confidence | Brier loss | Predicate accuracy |
| --- | ---: | ---: | ---: |
| B | 0.813 | 0.034969 | 1.0 |
| C | 0.084 | 0.839056 | 1.0 |

Python therefore did not improve the chosen action and substantially worsened
confidence calibration on this specimen.

## Resource accounting

For canonical run `run-005-d0073788d746`:

| Arm | Qwen calls | Input tokens | Output tokens | Qwen latency | Python calls | Python runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0 additional | 0 | 0 | 0 | 0 | 0 |
| B | 2 | 28,014 | 3,122 | 75.77 s | 0 | 0 |
| C | 2 | 28,296 | 3,273 | 79.26 s | 1 | 0.072 s |

The physical Qwen requests were serialized. Python time was negligible relative
to model time.

## Failure funnel

Canonical run:

| Stage | Count / outcome |
| --- | --- |
| Eligible battlefield | 1 |
| Sole-Executor route | 2/2 arms |
| Executor requests completed | 2/2 |
| Snapshot sufficient nominally | 2/2 |
| B verbal computation | 1 |
| C Python generated/executed | 1/1 |
| Ranked grounded proposals | 2/2 |
| Prospective checkpoints executable | 2/2 |
| Arbiter-authorized branches | 2/2 |
| Exact matched replays | 3/3 including A |
| B/C action change versus A | 2/2 |
| C action discrimination versus B | 0 |
| Favorable target-outcome changes | 0 |
| Harmful hard-risk changes | 0 |

Qualification attempts were preserved rather than overwritten. They localized
context overflow, malformed code, dynamic-reference vocabulary, and post-tool
finding provenance failures before the valid specimen.

## Controls

Sixteen deterministic tests cover battlefield selection, identity, abstention
coherence, Python provenance, executable/calibrated checkpoints, all frozen
verdict classes, coherent action relabeling, sole-policy no-trigger routing,
empty-history rejection, prompt compaction, immutable run namespaces, and full
snapshot delivery to C.

Nine inherited v0 authority tests also pass in an isolated pytest process. They execute the architectural
claims that B/C never calls R2's action selector, Semantic and Executor Qwen
contexts are logically isolated, Executor ledger events cannot change empirical
support, the Python sandbox is fresh/read-only, one-action chains are replayable,
and the primitive surface remains generic. The machine-readable record is
`artifacts/controls/static-authority.json`. Together, 25 tests pass.

The model-in-the-loop controls spent zero environment actions:

- Verbal B passed coherent action/effect permutation exactly: action 1 became
  action 2 under 1↔2 relabeling.
- After deletion of `t000`–`t007`, B attempted to cite removed IDs and the host
  firewall rejected it. C completed but did not produce a dependency-sensitive
  proposal.
- C also failed nominal dependency validation on the original control copy and
  did not remain treatment-compliant on the permuted fixture.

Thus nominal mechanism engagement is real, but perturbation robustness is not
yet adequate. The failed controls are retained as limitations, not tuned away.

## Replay and authority

The factual A prefix and all three one-step branches replay exactly. Qwen was
not called during factual environment replay. Generated code and proposals
created no empirical-support events. Only the recorded successor settled the
checkpoint. Each B/C branch executed one primitive and no remaining procedural
assumption received open-loop authority.

## Final interpretation

The dedicated procedural context was capable of producing a different legal,
well-predicted action, and its coherent-permutation response shows genuine use
of the supplied mapping. But at this boundary its action was not better than
frozen PCW on the preregistered outcomes.

Bounded Python was successfully delivered and causally cited, but it performed
only a shallow count, did not differentiate the policy from verbal reasoning,
and reduced calibration. Therefore:

```text
system-level benefit of verbal Executor vs frozen PCW: not demonstrated
system-level benefit of Python Executor vs frozen PCW: not demonstrated
code-mediated benefit of Python vs verbal Executor: not demonstrated
```

The right next move is not to add game-specific tools or planning. Freeze this
negative v0. A later preregistered intervention should test a stronger model or
a small generic computation representation while holding this action firewall
and the A/B/C causal structure fixed.
