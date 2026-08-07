# Deterministic developmental vertical-slice report

Date: 2026-08-03. Scope: exactly one executable observe/predict/act/compare/
update/rewrite loop; no broader research features.

## Result

The synthetic environment now runs three action-conditioned transitions. The
first grounds a changed-coordinate regularity, the second confirms its causal
prediction, and the third deliberately moves the changed coordinate and
falsifies it. All cognition below is executable Schema Calculus, not a
retrospective dashboard annotation.

```text
actions:                [1, 2, 1]
prediction confirmation: true
prediction failure:     true
failed diagram:         true
evidence after failure: attempts=2 confirmations=1 failures=1 confidence=0.5
rewrite committed:      true
final Mind revision:    9
```

The failure produced two immutable rewrite tasks. Serial and two-process modes
returned identical results and ranking. Collection uses `as_completed`, then a
stable objective/complexity/identifier ordering, so completion order cannot
select a different rewrite. Evaluation left the serialized live Mind unchanged;
the coordinator then revoked `schema-c89ada30cc38d411` and added the selected
`schema-d15ee9bbc95a4958` while preserving its evidence.

## Real semantic examples

Executable causal schema:

```text
context_action_predicts_changed_coordinates:
    Product[Context, ActionId] -> PredictedResult
    body: predict(compose(identity, primitive(context_action_prediction)))
```

Confirmed prediction at step 1:

```text
predicted: (changed coordinates ((0,0),), action 2)
actual:    (changed coordinates ((0,0),), action 2)
compare:   true
evidence:  (1 attempt, 1 confirmation, 0 failures, 0.6666666666666666)
```

Failed diagram at step 2:

```text
causal_prediction: ((0,0), action 1)
world_transition:  ((0,1), action 1)
commutes: false
diagram hash: 85c99d04df02f08b6843d7c61dfc04fa6882796199f1b7fec4c0ccc3f056d397
```

Committed rewrite:

```text
candidate: rewrite-1dc8d5ace9618fd97cd2
old hash:  c89ada30cc38d411241dc60028a78f36745506308fa57cff3f2ab92ec5f1c99f
new hash:  d15ee9bbc95a495842cbfc86c577a058f1c3daef47f4cf7b40ff41204389c690
reason: controlled prediction failure triggered a transparent structural rewrite
```

The rewrite is intentionally simple and semantics-preserving on registered
cases. This milestone proves explicit, pure evaluation and transactional change;
it does not claim successful accommodation to the violated rule.

## Dashboard evidence

Live mode and replay mode consume the same append-only `TraceEvent` objects.
The localhost acceptance run exposed 18 events, three synchronized action
steps, actions `[1,2,1]`, agreement states `[N/A,true,false]`, the two evidence
updates, failed diagram, ranked rewrite candidates, and committed Mind change.
The saved replay API returned the same sequence, with event hash
`bebb61d784f530fea5004834093ba417daa7728c35d2e04a3415e8813822c6c1`.

The UI displays current and next frames, observations, legal/current/previous
actions, grounded S0 outputs, typed active schemas, action and rewrite
candidates with rejection reasons, selected schema, predictions, actual
properties, agreement/failure, evidence counters/confidence, failed diagram,
rewrite and Mind transactions, score/level/resets/budget, activation graph, and
raw events. Play, pause, previous, single-step, timeline, speed, live, and saved
replay modes are available. The UI never calls or controls policy inference.

## Exact files changed for this milestone

```text
README.md
schema_calculus/types.py
schema_calculus/composition.py
schema_calculus/checker.py
schema_calculus/complexity.py
schema_calculus/interpreter.py
schema_calculus/primitives.py
mind/library.py
runtime/episode.py
runtime/policy.py
learning/__init__.py
learning/rewrite_candidates.py
evaluation/replay.py
dashboard/trace_views.py
dashboard/server.py
submission/agent.py
tests/unit/test_calculus.py
tests/unit/test_mind.py
tests/integration/test_dashboard.py
tests/integration/test_policy_parallel.py
tests/integration/test_rewrite_parallel.py
tests/replay/test_vertical_slice.py
tests/kaggle/test_submission.py
docs/DSL_SPEC.md
docs/SEMANTICS.md
docs/DASHBOARD.md
docs/PROGRESS.md
docs/VERTICAL_SLICE_AUDIT.md
docs/FINAL_REPORT.md
```

## Exact verification commands and results

Baseline before implementation:

```text
python3 -m pytest -q
25 passed

/home/pauloabelha/reflector_old/.venv/bin/ruff check .
All checks passed!

PYTHONPATH=/home/pauloabelha/reflector_old/.venv/lib/python3.12/site-packages \
  python3.12 -m mypy schema_calculus mind runtime learning evaluation \
  dashboard submission parallelism
Success: no issues found in 43 source files
```

Final gate:

```text
python3 -m pytest -q
31 passed

/home/pauloabelha/reflector_old/.venv/bin/ruff check .
All checks passed!

/home/pauloabelha/reflector_old/.venv/bin/ruff format --check .
54 files already formatted

PYTHONPATH=/home/pauloabelha/reflector_old/.venv/lib/python3.12/site-packages \
  python3.12 -m mypy schema_calculus mind runtime learning evaluation \
  dashboard submission parallelism
Success: no issues found in 44 source files

python3 -m evaluation.replay --output /tmp/reflector-vertical-final
prediction_success=true prediction_failure=true failed_diagram=true
rewrite_accepted=true actions=[1,2,1]

python3 -m submission.smoke_test
2
```

Live/replay HTTP commands exercised:

```text
python3 -m dashboard.server --live-synthetic \
  --output /tmp/reflector-developmental-live/trace.json \
  --step-delay 0.3 --port 8877
curl -s http://127.0.0.1:8877/api/trace

python3 -m dashboard.server \
  --trace /tmp/reflector-developmental-live/trace.json --port 8878
curl -s http://127.0.0.1:8878/api/trace
```

Both APIs returned three steps and actions `[1,2,1]`; replay returned the same
18 event objects.

## Identities

```text
source hash:          f93c6aefa4281fd296e056d6c4bc15f59c50ea631bbe14e6b7d1f67ba40c50ea
DSL version:          0.1
DSL_SPEC.md SHA-256:  07e355d474266af066c344bb5542a72353ae6902e607f29c18921f4bc6009c3f
serialized Mind hash: 52fb9b5bb5d56ac5d8c9572261cca511a2f69e782a8ffb5d876f31ec33d1131b
mind.json SHA-256:    323fc38f2feeb28e3c2430505c2c8d8b4d541b2b8691abc0ee8024146733e913
trace hash:           73fca004a57f8a86f23539ea15f4fee28b06c1a64e0ed15918642a80e6394b11
```

## Kaggle identity and remaining uncertainty

`SubmissionPolicy` and local execution both instantiate `RuntimePolicy`, which
executes selected action schemas through the same checker/interpreter. Tests
cover serialized-Mind identity, legal actions, submission budget exhaustion,
and deterministic overlay contents. The overlay contains no `dashboard/`
package. The optional official class is still a lazy boundary because the
actual Kaggle gateway/starter runtime was not available in this fresh checkout;
live Kaggle lifecycle behavior therefore remains unverified.

## Deliberately unimplemented research features

Compression, analogical transport, composability loss, automatic reification,
primitive-extension loss, probabilistic salience, and large-scale ARC
strategies remain unimplemented and unclaimed. Existing analogy and primitive
proposal scaffolds are disconnected from this loop. The synthetic result is
evidence of deterministic executable semantics, not ARC-AGI-3 competence.
