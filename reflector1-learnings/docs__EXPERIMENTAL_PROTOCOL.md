# Experimental protocol

Every run manifest records source hash, engine and DSL versions, Mind hash,
game/level label when available, run seed, worker count, requested and effective
execution mode, task threshold, legal actions, and artifact hashes. Synthetic,
replay, local public-development, Kaggle public, and Kaggle private evidence
must remain distinct.

Preregister comparisons over task-only, MDL, primitive cost, equilibration,
full objective, and analogy/reification ablations. Freeze candidate generation
before held-out evaluation. A change is retained only after multi-game evidence
and regression preservation. Hidden score is the ultimate criterion; internal
loss and synthetic success are proxies.

## Two-level operational experiment v1

The frozen preregistration is
`evaluation/two_level_preregistration.json`. Both levels are in `k=1`: one
exposed singleton legal-action relation determines one one-step transition.
Level A exposes action `1`; Level B uses different pixels and exposes action
`2`, so replaying A is illegal on B. The expected relational connection is
stored only as a SHA-256 commitment until after results are computed.

All O/M/Q/R/E conditions begin from the byte-identical overfit Mind and Level A
experience. Each has a twelve-candidate ceiling, a two-action development
budget, and a two-action transfer budget. Candidate evaluation is immutable;
only `MindCoordinator` commits additions, rewrites, or explicit pruning.

The MDL compressor evaluates deletion and constant-parameterization candidates.
The relational selector is fully complexity-counted and slightly larger than
the literal selector, so MDL alone rejects it. The equilibrium treatment accepts
it only when the separately recorded exception burden offsets that description
increase under frozen weights. The operational diagram compares only paths
declared equivalent on registered Level A cases.

```bash
python3 -m evaluation.two_level_experiment --output artifacts/two-level-v1
python3 -m dashboard.server --trace artifacts/two-level-v1/trace.json --port 8766
```
