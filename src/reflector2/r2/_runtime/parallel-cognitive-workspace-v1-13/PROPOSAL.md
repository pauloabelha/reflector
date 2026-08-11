# Parallel Cognitive Workspace v1.13

v1.13 is a separately versioned replacement for the implementation-invalid
v1.12 run. Every scientific, model, context, action, probe, schedule,
checkpoint, and causal gate remains frozen from v1.12.

The sole change is phase-correct strict revision dispatch:

- An ambiguity/unbound repair turn uses the small revision-or-abstain contract
  and requires exactly the current relation-set address. It cannot require
  prospective evidence because no probe has occurred yet.
- A later causal evidence-return turn uses the same small contract and requires
  both the current relation-set address and one prospective environment-evidence
  address from the compact causal packet.

Both phases delegate semantic compilation to the unchanged authoritative
compiler. No prior response, schema, explanation, workspace, action ledger,
notes, or solution trace may seed either fresh arm.
