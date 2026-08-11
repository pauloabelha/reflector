# Explanation-guided one-action control v0

This experiment keeps semantic Qwen out of the motor path. Qwen writes
schemas, explanations, attention, and a bounded unverified working note. R2
chooses exactly one legal primitive, the arbiter commits it, and the
environment settles it before the next choice.

Run the validated `ar25` episode:

```bash
.venv/bin/python experiments/explanation-guided-one-action-control-v0/experiment.py --run --game ar25
```

From `/home/pauloabelha/reflector2`, watch a fresh run in the agent arcade:

```bash
.venv/bin/python experiments/explanation-guided-one-action-control-v0/experiment.py --arcade --game ar25
```

Then open <http://127.0.0.1:8767/arcade>. Choose any installed public game and
starting level, or select a stored run for causal playback. The page shows the live grid,
current objective and explanations, Qwen scratchpad, selected one-action
rationale, and the latest settlement. It supports pause/resume, single-step,
scrubbing, and 0.25x through 10x playback. Each browser-started episode uses a
fresh artifact directory under `arcade-runs/`. Its manifest retains the R2
version, protocol, source hashes, configuration, game, and starting level.

Before action 1, the runner blocks for the first semantic Qwen turn and grounds
the initial explanation set from frame 0. That set is never empty: under the
explicit solvable-game and hypothesis-family completeness assumptions, it
contains at least one winning explanation even though R2 initially does not
know which candidate it is.

The local Qwen endpoint configured by the inherited protocol must be running
at `127.0.0.1:8081`.

Qwen is managed independently as an always-up user service. Arcade restarts do
not restart the model:

```bash
systemctl --user enable --now reflector-qwen.service
systemctl --user status reflector-qwen.service
curl -sS http://127.0.0.1:8081/health
```

For logs or a deliberate model restart:

```bash
journalctl --user -u reflector-qwen.service -f
systemctl --user restart reflector-qwen.service
```

## Validated result

- Game: `ar25`
- Level completed: 1
- Actions: 38
- Qwen semantic turns: 4
- Working notes persisted: 4
- Exact factual replay: passed
- Exact counterfactual replay: passed
- Support-authority violations: 0
- Break-in: unique revised binding confirmed at action 25; R2 entered control
  at action 26.

The main known cost is workspace growth: the completed run contains 15,857
objects, dominated by 9,746 `r2_binding` and 2,432 `shadow` objects. The policy
costs no additional ARC points, but late cycles become slow. Compacting these
derived inspection objects is the next performance target.

## Role-grounding scaling invariant

Defeasible role grounding still evaluates every ordered role tuple admitted by
the existing enumeration budget. Its Pareto pass indexes candidates only by
exact equality of the residual dimensions used by dominance. One representative
is compared per exact vector, then every member of each nondominated vector is
restored in original enumeration order before the unchanged rank and top-k
rules. Thus the index cannot discard a distinct or true grounded role binding
for speed.

On the audited 64-region FT09 frame, all 4,032 ordered pairs were retained for
feature evaluation but occupied only 29 exact dominance vectors. The indexed
pass reduced measured grounding time from about 10.1 seconds to 1.8 seconds;
contracts compare its complete front and final grounded bindings against the
exhaustive algorithm.
