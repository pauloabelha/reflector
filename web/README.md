# Reflector replay console

This is a strict TypeScript, browser-native frontend for the local Reflector
analysis API. It has no runtime framework, CDN, font, telemetry, or remote
service dependency.

## Live mission control

Build once, then launch the read-only workspace monitor:

```bash
cd web && npm run build && cd ..
.venv/bin/reflector dashboard
```

Open `http://127.0.0.1:8765/monitor.html`. The page receives one snapshot per
second over a server-sent event stream. It auto-discovers cognitive JSONL
streams, candidate lineage, official scorecards, per-game bests, the
Games × Levels matrix, and recent report artifacts under the workspace.

For a browser-paced official run, set `REFLECTOR_LIVE_ACTION_DELAY_MS` on the
local harness command. This development-only delay is capped at two seconds,
defaults to zero, and does not alter the symbolic inference configuration:

```bash
REFLECTOR_LIVE_ACTION_DELAY_MS=500 .venv/bin/reflector official-isolated-run …
```

Use `--workspace`, `--host`, or `--port` to override their local defaults.
The monitor is read-only and does not import or alter game implementations.

Build it once:

```bash
cd web
npm install
npm run build
cd ..
```

Generate or select a trace, then start the same Python repository:

```bash
.venv/bin/reflector trace-demo --output /tmp/reflector-trace.json
.venv/bin/reflector web /tmp/reflector-trace.json
```

To enable the population laboratory:

```bash
.venv/bin/reflector web /tmp/reflector-trace.json \
  --db /tmp/reflector-experiments.sqlite
```

Open `http://127.0.0.1:8765`. The server binds only to loopback by default.
Use Space to play/pause and the arrow keys to single-step.

The branch tool replays a deployable `MindConfig` over recorded observations.
It measures policy divergence and predicted effects, but cannot produce
counterfactual environment states or score changes from a fixed trace.
