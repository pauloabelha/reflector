# Reflector replay console

This is a strict TypeScript, browser-native frontend for the local Reflector
analysis API. It has no runtime framework, CDN, font, telemetry, or remote
service dependency.

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
