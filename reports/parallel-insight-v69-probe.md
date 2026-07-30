# v69 parallel cross-game insight probe

Date: 2026-07-30  
Candidate: `candidate-2336bc12a0bc28de`  
Inference fingerprint:
`82a5cb4ae5d5f6a6a813ec3a9b6bef4c609152a02358ba787d9c3aab4e3b893c`

This is a development triage experiment, not a promotion score. Four
currently unsolved games ran in separate isolated processes with four workers
and one cognitive event per action. The reusable runner is
[`scripts/run_parallel_insight_probe.py`](../scripts/run_parallel_insight_probe.py).

| Game | Levels | Actions | Longest plateau | Mechanism-advisor actions | Causal P/C/X | Evidence-ranked triage signal |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `bp35` | 0/9 | 400 | 400 | 48 | 0/0/0 | Mechanism actions lacked prospective transition or goal evidence. |
| `dc22` | 0/6 | 400 | 400 | 52 | 0/0/0 | Mechanism actions lacked prospective transition or goal evidence. |
| `ka59` | 0/7 | 400 | 400 | 24 | 0/0/0 | Mechanism actions lacked prospective transition or goal evidence. |
| `sc25` | 0/6 | 400 | 400 | 16 | 0/0/0 | Mechanism actions lacked prospective transition or goal evidence. |

The shared cross-game signal is not a proposed game rule. It says that the
current mechanisms sometimes selected nonbaseline actions, but none emitted a
prospectively testable causal prediction on these games. This ranks
transition/goal representation ahead of additional undirected exploration as
the next trace-inspection question.

The first analyzer version incorrectly classified every expected
`no-unique-*` advisor abstention as a mismatch. Validation caught this and the
final analyzer distinguishes non-applicability from explicit ambiguity,
quarantine, conflict, or transition mismatch.

Reproduction:

```bash
.venv/bin/python scripts/run_parallel_insight_probe.py \
  bp35 dc22 ka59 sc25 \
  --config candidates/v69-colored-stencil-primary-400.json \
  --environments-dir /home/pauloabelha/arc-agi-3-public-games-2026/environment_files \
  --output-dir /tmp/reflector-parallel-insight-v69 \
  --workers 4 \
  --timeout 900
```
