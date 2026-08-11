# Parallel Cognitive Workspace v1.15

v1.15 is a separately versioned replacement for the graph-invalid v1.14 run.
It inherits every cognitive, controller, prompt, context, call, action, probe,
checkpoint, replay, and causal-attribution rule unchanged.

The sole repair is idempotent prospective-criticism materialization. For each
Qwen schema, the evidence-return bridge computes the exact cumulative probe
packet and its stable criticism key. If that criticism already exists, later
control transitions do not recreate the same identity from a newer grounding
snapshot. A genuinely novel probe packet still creates a new immutable
criticism. Every environment transition and evidence object remains durable;
this rule changes neither evidence authority nor controller behavior.

No v1.14 schema, response, controller state, workspace, action ledger, notes,
or solution trace may seed either fresh v1.15 arm. Preserved artifacts are used
only for crash regression and replay/interface verification.
