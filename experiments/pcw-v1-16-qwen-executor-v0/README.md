# PCW v1.16 + Qwen Executor v0

This isolated mechanism experiment starts from the exact frozen Parallel
Cognitive Workspace v1.16 solver and compares three causal arms on `ar25`:

- **A — frozen PCW v1.16:** the original semantic-Qwen/R2 controller, unchanged;
- **B — verbal Executor:** a separate procedural Qwen context is the sole
  source of concrete legal action proposals;
- **C — Python Executor:** the same Executor contract with bounded ephemeral
  Python over an immutable workspace/history snapshot.

Arms B and C use one physical Qwen server and the same serialized request
queue as the semantic worker. They do not share prompts, cursors, private
summaries, chat state, or KV state. All cross-worker information is durable
workspace data.

The live B/C action funnel is:

```text
workspace -> semantic/R2 epistemic update -> Executor ranked proposal
          -> arbiter validation -> one primitive environment action
```

R2 supplies grounded objects, bindings, predictions, contradictions, evidence,
and constraints. It does not select the live B/C action. The semantic worker
does not name legal ARC actions. The Executor is the only policy head, while
the arbiter remains the only action-commit authority.

Executor is defined narrowly as the sole motor-policy worker, not as another
general reasoner and not as a reranker for the frozen PCW score. Its immutable
input contains the precise current frame, legal opaque actions, grounded and
semantic workspace objects, R2 predictions/contradictions/constraints, and the
complete relevant transition history with raw frames, deltas, animation, and
provenance. Arm C may compute freely but ephemerally over that packet. Both
arms expose only a compact ranked proposal: one action, live dependencies,
subgoal/desired delta, a qualitative value case, a one-step observable
checkpoint, and an invalidation condition.

The governing asymmetry is: **free internal computation is cheap; real actions
are precious.** Within the preregistered budgets, Executor should compute and
falsify freely before spending one action. Opaque action meanings alone do not
justify paralysis; they make a safe, high-discrimination one-step probe more
valuable.

The arbiter is a validity gate rather than a second policy. It checks legality,
freshness, sole-source authority, dependency liveness, hard contradictions,
and checkpoint prospectiveness. It never substitutes an action. Every observed
successor settles the proposal into a new environment-authored workspace
object before the next decision, so mismatch returns control to the shared
epistemic loop immediately. The interface leaves room for later milestone
proposals without granting v0 multi-step execution authority.

## Frozen v0 tool boundary

Arm C exposes only `run_analysis(code)` with the preregistered
`executor-generic-primitives-v0.1` surface in `executor_primitives.py`: stable-ID
workspace/history queries, Manhattan distance, bounding boxes and generic box
relations, exact grid diffs, and BFS over a caller-supplied graph. These are
semantic-free operations over information already materialized by PCW; there
are no role detectors, palette meanings, opaque-action meanings, game rules,
world models, milestone planners, skills, or open-loop action queues. The
manifest records the primitive source hash before live comparison.

If generated code names a missing primitive or Qwen explicitly reports one,
the run records `SNAPSHOT_OR_TOOLING_INSUFFICIENT`. The primitive surface is not
expanded during v0; repeated generic gaps are candidates for a separately
preregistered v1. Python results remain computation and never create empirical
support.

## Clean source boundary

The frozen solver is pinned to commit
`3da145b8d0f502c393d3fd9c6dc7d4a2d53d68ca`. `source_guard.py` verifies every
loaded v1.16 inheritance-chain source file against that commit before a live
run. Arm A delegates directly to the guarded frozen entry point. The new code
does not edit or monkeypatch `src/reflector2` and does not alter frozen files.

## Layout

```text
protocol.py          immutable snapshot and proposal contracts
analysis_sandbox.py  bounded fresh-process Python tool used only by C
executor_primitives.py frozen small generic primitive surface for C
executor_worker.py   isolated two-stage Executor calls and durable records
policy.py            sole-policy adapter for B/C
runner.py            explicit episode orchestration
experiment.py        manifest, CLI, accounting, and verdict assembly
source_guard.py      pinned-source verification
artifacts/           protocol, arms, controls, counterfactuals, replay
```

## Commands

Run contract and fixture controls without opening ARC or calling Qwen:

```bash
.venv/bin/python experiments/pcw-v1-16-qwen-executor-v0/experiment.py --controls
```

Materialize the frozen protocol and source hashes:

```bash
.venv/bin/python experiments/pcw-v1-16-qwen-executor-v0/experiment.py --dry-run
```

Live A/B/C execution requires the configured local Qwen server:

```bash
.venv/bin/python experiments/pcw-v1-16-qwen-executor-v0/experiment.py --run
```

No leaderboard claim follows from this development-game experiment.
