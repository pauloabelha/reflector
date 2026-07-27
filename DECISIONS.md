# Decision log

## 2026-07-27 — Official starter is the repository root

Reflector was cloned directly from `arcprize/ARC-AGI-3-Agents`. The official
`Agent`, `Swarm`, and `main.py` lifecycle remains the execution shell.

## 2026-07-27 — One dependency-free policy core

All decisions live in `reflector.SymbolicPolicy`. Local and Kaggle adapters
translate protocol objects only. Generated notebooks embed the package; they do
not contain a separately maintained policy.

## 2026-07-27 — Inference closure is explicit

The Kaggle overlay uses an explicit inference-file allowlist. Optional LLM
agents retained from the starter are development-only and are no longer
imported by the core agent registry.

## 2026-07-27 — Offline compatibility is executable

`kaggle_smoke_test` uses a clean directory and Linux network namespace rather
than treating an environment flag as evidence that networking is disabled.

## 2026-07-27 — First symbolic language is constrained and empirical

The first DSL is composed of typed atoms, objects, events, scenes, transitions,
schemas, and synthetic concepts. Visual objects are same-color connected
components with greedy persistent identity matching. These are explicit
approximations. Concepts require repeated action-effect evidence and positive
utility after a description-complexity charge.

## 2026-07-27 — Counterfactual claims are bounded by observable evidence

Trace replay may credit description-length reduction, avoided rediscovery, and
repeated planner work. It must report zero action savings unless an actual
branch-and-replay environment run supplies the counterfactual outcomes.
Causal strength is an observed action/control rate difference with discounted
confidence, not a claim of complete causal identification.

## 2026-07-27 — The deployed configuration is the evolutionary genome

Population candidates are strict, bounded `MindConfig` values instantiated by
the same `SymbolicPolicy` shipped to Kaggle. Mutation providers return
untrusted structured patches; they cannot inject or replace policy code.
Candidate validation runs twice in a fresh network-disabled process before
SQLite persistence and Pareto comparison.

## 2026-07-27 — Transformed traces are robustness probes, not game rollouts

Seeded color permutations test representational retention while preserving
recorded outcomes. They do not model counterfactual environment dynamics and
cannot by themselves support claims about RHAE, action savings, or score
improvement.
