# Live and replay dashboard

The dashboard is a read-only consumer of the runtime's canonical append-only
events. It never invokes `RuntimePolicy` in the browser or HTTP request path.
In live synthetic mode, the server starts the same
`evaluation.replay.run_synthetic` episode used by deterministic replay and
passes only an `AppendOnlyTrace.append` event sink into it.

Live storage is JSONL: one canonical `TraceEvent` per flushed line. Completion
finalizes those exact event objects into the standard replay JSON document.
`action_steps` is a read-only presentation projection that joins related events
by their emitted step number; it does not become a second canonical record.

## Live acceptance walkthrough

```bash
python3 -m dashboard.server \
  --live-synthetic \
  --output artifacts/live/trace.json \
  --step-delay 1.0
```

1. Open <http://127.0.0.1:8765>. The episode starts on the first API poll.
2. Watch the candidate transaction appear before its actual transition.
3. Select **Pause** to stop following the newest UI step, then use **Previous**,
   **Single-step**, or the timeline slider to inspect it.
4. Inspect frames, actions, legal actions, typed schemas, candidate outcomes,
   predictions, mismatches, metrics, updates, activation graph, and raw events.
5. Stop the server after it reports completion.
6. Start replay mode over the saved canonical trace:

   ```bash
   python3 -m dashboard.server --trace artifacts/live/trace.json
   ```

7. Use **Play** and the speed selector to replay. Actions and schema events are
   identical because live and replay read the same event objects.

Pausing the UI intentionally does not pause or change the agent. It freezes the
selected presentation step for scientific inspection while runtime decisions
continue independently.

## Automated evidence

`tests/integration/test_dashboard.py` runs a live episode through the JSONL
sink, waits for finalization, loads the saved replay independently, and requires
exact equality of canonical events plus action and schema projections. It also
checks every step for both observations, next legal actions, budget, schema
types, and candidate rejection-reason fields.

The developmental-loop HTTP smoke produced 18 canonical events and three
action steps. It showed actions `[1, 2, 1]`, agreement states
`[not-applicable, true, false]`, evidence updates `(1,1,0,2/3)` then
`(2,1,1,0.5)`, one failed diagram, and one committed rewrite. The replay API
returned the same events. Event hash:
`bebb61d784f530fea5004834093ba417daa7728c35d2e04a3415e8813822c6c1`.
