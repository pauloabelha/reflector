# Decision log

## 2026-07-27 — Official starter is the repository root

Reflector was cloned directly from `arcprize/ARC-AGI-3-Agents`. The official
`Agent`, `Swarm`, and `main.py` lifecycle remains the execution shell.

## 2026-07-27 — One dependency-free policy core

All decisions live in `reflector.SymbolicPolicy`. Local and Kaggle adapters
translate protocol objects only. Generated notebooks embed the package; they do
not contain a separately maintained policy.

## 2026-07-27 — Inference closure is explicit

The Kaggle overlay allowlist is four files. Optional LLM agents retained from
the starter are development-only and are no longer imported by the core agent
registry.

## 2026-07-27 — Offline compatibility is executable

`kaggle_smoke_test` uses a clean directory and Linux network namespace rather
than treating an environment flag as evidence that networking is disabled.
