# Completion audit

| Requirement | Evidence | Status |
| --- | --- | --- |
| Frozen A is exact PCW v1.16 | separate candidate plus exact A branch replay | proved |
| B is verbal Executor without Python | treatment record, zero Python calls | proved |
| C differs only by bounded Python | matched prompts/budgets and treatment record | proved |
| Executor sole B/C proposal source | route invariant and proposal provenance | proved |
| Arbiter sole commit authority | branch runner consumes only validated proposal | proved |
| One physical Qwen, isolated contexts | one serialized queue; arm-specific context/provenance; inherited executable isolation test | proved |
| One primitive action at a time | one branch action per arm | proved |
| Ranked legal, grounded, checkable output | validated candidates and typed checkpoints | proved |
| Full relevant history available | 25 loss-auditable transitions; full snapshot in C | proved |
| Code is computation, not support | support-authority architecture, no empirical writes, and inherited executable support-authority test | proved |
| Generic frozen primitive set | version/hash in identity and manifest | proved |
| No semantic helper expansion | source audit and unchanged primitive source hash | proved |
| Same-state causal comparison | identical prefix digest; three exact branches | proved |
| C treatment truly engaged | successful Python, durable return, cited computation/finding | proved |
| B>A and C>B answered separately | `system_comparisons` and `verdict` | proved |
| Dependency deletion control | model-in-loop artifacts; host rejection | ran, failed robustness |
| Coherent action/effect permutation | B equivariant 1→2 | passed for B, C failed robustness |
| No-successor leakage | decision boundary has `successor_available=false`; prefix cut at seq 711 | proved |
| Worker isolation | complete stateless request packets, separate context identifiers, and `artifacts/controls/static-authority.json` | proved |
| Exact replay | `exact_replay=true` | proved |
| Resource accounting | per-arm result records and `results.md` | proved |
| Failure funnel | qualification namespaces and canonical funnel | proved |
| Honest scope/transfer claim | negative single-boundary verdict | proved |

The failed live robustness controls do not invalidate the nominal matched causal
specimen; they prevent any claim that the interface is generally robust.

The final executable audit comprises 16 experiment-local tests plus 9 inherited
v0 authority/isolation tests (25 passing tests total), run in separate pytest
processes to isolate their same-named top-level experiment modules. The inherited suite also
proves that the B/C policy route never invokes the R2 action selector, Executor
events cannot alter empirical support, the two Qwen roles remain logically
isolated, the sandbox is fresh/read-only, and one-action chains are replayable.
