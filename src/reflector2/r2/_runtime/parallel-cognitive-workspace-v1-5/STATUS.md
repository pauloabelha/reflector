# Parallel Cognitive Workspace v1.5 status

## 2026-08-09 — correction preflight

- One change from v1.4: graph-visible prospective evidence uses the existing
  anonymous intervention reference and omits redundant raw `action_id`.
- Fresh artifacts only; no prior cognitive state is imported.
- Live run not started.

## 2026-08-09 — terminal result

- Binary verdict: `INVALID` (controller/witness status integration defect).
- Control: 48 actions, level 0, exact replay.
- Shared: stopped at action 9 after one live Qwen proposal and one prospective
  ambiguity probe.
- Positive partial mechanism: Qwen proposed `SameOutline -> Decrease TAR`; R2
  preserved three candidate effect pairs, chose an intervention on which their
  predicted outcomes differed, and all three exact predictions matched the
  directly observed transition.
- Exact defect: the ambiguity witness's diagnostic `status` overwrote the
  controller's `ambiguous-active` status. The schema was not marked activated,
  was retried as a duplicate, and an empty duplicate population reached a graph
  binding index operation.
- A status-preserving correction is versioned as v1.6. No v1.5 artifacts are
  reused as cognition.



## 2026-08-09 10:40:49 — live census launched

- Jobs: 2; games: 1; profiles: 1; environment workers: 2.
- FAILED `generic_prospective/ar25/shared_live_qwen`: IndexError: tuple index out of range.
- COMPLETE `generic_prospective/ar25/r2_only`: levels=0, actions=48, Q→R grounded=0, replay=True.
