# Parallel Cognitive Workspace v1.12 status

## 2026-08-09 — preregistration and offline preflight

- No v1.12 ARC environment has been opened and no v1.12 Qwen request made.
- Preserved v1.11 action-16 artifacts were used only as offline packet,
  compiler, and size fixtures.
- The previous 17,873-unit recursive closure renders as a 6,342-unit compact
  compiler turn under the unchanged 6,400 frontier budget.
- The revision response schema shrinks from 7,483 to 1,468 bytes and exposes
  only revision or abstention.
- Pending: preserve all unresolved selected judgments, validate temporal
  grounding integration, run the combined suite/dry-run, verify resident server,
  and checkpoint before any reset.

## 2026-08-09 — freeze ready

- The final packet preserves and decodes all 12 canonical probe judgments:
  eight selected/modelled supports and four unselected/unmodelled unresolved
  alternatives. Every row retains proposal, transition, frame, evidence,
  prediction, graph/controller binding, candidate/effect-pair, model, residual,
  delta, selection, verdict, and reason fields. No dependency closure traversal
  occurs.
- Final compact compiler turn: 5,923/6,400 estimated units on the preserved
  worst checkpoint. The full offline multimodal request used 10,586 prompt
  tokens. A 3,072 completion reserve leaves 10,918 tokens of the 24,576 window.
- The revision grammar makes relation and prospective evidence address classes
  separate mandatory fields, so their conjunction is structurally enforced.
  Offline Qwen completed the strict response in 1,178 tokens with
  `finish_reason=stop`; its response is diagnostic only and cannot seed the
  fresh run.
- Action-free temporal relations and before/after frame-digest provenance now
  enter the complete grounding packet used by both validation and later R2
  activation. No opaque action token is exposed.
- Combined v1.9/v1.12 and focused cognition suites pass (`39 passed` across the
  two invocations), along with dry-run manifest construction, compilation, and
  `git diff --check`.
- No v1.12 ARC environment has been opened. The next step is server recheck,
  git checkpoint, then one fresh paired run.
