# Parallel Cognitive Workspace v1.18 — unique-binding calibration

v1.17 was a valid negative on wa30: Qwen eventually produced one complete,
unique binding, but all target-local action effects were unknown. The planner
could select only modeled predictions, so it fell back forever and generated
no causal evidence for Qwen or control.

wa30 is now a development target. A v1.18 success is a mechanism repair, not a
fresh held-out transfer claim. A later version must run unchanged on another
mechanically selected game before making that claim.

The sole cognitive capability added here is generic calibration:

1. For exactly one complete grounded Qwen binding with no operator-improving
   modeled action, select an unseen legal opaque intervention deterministically.
2. Commit the selected prediction as unknown (`modeled=false`, null predicted
   delta/residual) before acting.
3. Direct correspondence produces a calibration sample. Store its exact action
   effect, including `(0,0)`, under this binding only. The sample has support
   delta zero and cannot confirm a schema, prediction, or binding.
4. Return the exact selected calibration outcome to Qwen as structured
   criticism. Qwen may revise or abstain.
5. Only a later fresh modeled prediction that matches a direct outcome may
   confirm a revised binding and authorize control.

Calibration has an independent cap of eight actions and cannot borrow the four
ambiguity probes or one reserved revision-confirmation probe. Qwen receives one
additional scheduled turn at action 32 so evidence from a schema integrated at
action 24 can be considered. No game, predicate, entity, pair, direction,
coordinate, action ID, action meaning, or wa30 outcome is encoded.

Mechanism success requires a durable calibration sample, an evidence-return
criticism, an evidence-citing non-alpha revision, a uniquely confirmed revised
binding, a changed control decision, and a favorable exact same-state branch.
Level completion is a separate score success. All inherited validity gates and
empty-workspace prohibitions remain authoritative.
