# R2 glue: eight-hour live integration charter

Started: 2026-08-12T02:42:48Z  
Branch: `glue`  
Baseline: `75600da` (`origin/main`)

## Objective

Make Reflector II behave as one smooth epistemic control system across ARC-AGI-3
games. Begin with live AR25 because its failure is observable and already has a
causal trace, but treat it only as a diagnostic case. The target is generic
game-entry competence: acquire a world model quickly, select efficient
experiments, form grounded goals, exploit supported dynamics, and revise at the
first contradiction.

This experiment does not claim that eight hours of engineering will establish
Kaggle competitiveness. It will produce a source-pinned architecture, live
evidence, failures, checkpoints, and the strongest truthful next boundary that
the evidence supports.

## Non-overfitting contract

Production control code must not contain:

- public game identifiers or level numbers;
- named colors, visible object counts, or named puzzle shapes;
- mappings from opaque action IDs to semantic directions or operations;
- a desired AR25 route, terminal board, or known solution trace;
- score or success inferred from a visual pattern rather than the environment;
- a semantic rule such as “holes imply fitting.”

AR25-specific material may exist only in experiment artifacts, replay fixtures,
and reports. A production change is eligible only when it is stated as a generic
capability, has synthetic counterexamples, and survives a non-AR25 or
game-agnostic test.

## Priors and evidence

Priors are allowed but must remain explicit and defeasible.

| Layer | May contain | May not do |
|---|---|---|
| Semantic priors | verbs, topology, objecthood, containment, negative space, analogy, candidate goals | assert grounding, action meaning, support, or success |
| Measurement primitives | bounded geometry and temporal operators with declared semantics | choose which concept applies |
| Qwen abduction | propose concepts, relations, measurements, experiments, and alternatives | execute actions or promote its own claims |
| R2 grounding | bind typed roles and compile bounded measurements | silently reinterpret an unmeasurable proposal |
| R2 causal control | predict, rank, authorize one action, and invalidate on contradiction | learn from a hypothetical successor |
| Environment | observations, transitions, level/score effects | provide semantic explanations |

Every retained prior will be labeled `PRIOR`; every environment-supported claim
will cite transition evidence; every plan remains prospective until settled.

## Live loop

```text
observe exact visual/transition evidence
→ Qwen proposes several action-free explanations and discriminating questions
→ R2 grounds what it can and preserves the rest as OPEN, not discarded prose
→ R2 selects one progress or information action under explicit cost/risk
→ publish frame + prediction + settlement atomically
→ revise hypotheses, identities, effects, goals, and memory
→ stop queued behavior at first contradiction
```

## Promotion gates

A change may be merged into the glue architecture only when:

1. its game-neutral contract is written before interpreting the result;
2. authority remains model proposal → R2 validation → environment settlement;
3. failure is explicit and does not fall back to invented semantics;
4. focused tests cover positive, ambiguous, and adversarial cases;
5. source search finds no game/action/color/route leakage;
6. at least one live or held-out trace exercises the intended handoff;
7. reports distinguish implemented, observed, inferred, and prospective claims.

## SOTA evidence used

The local August 2026 Kaggle/forum audit supports a hybrid architecture:

- competitive systems use strong local VLM/coding priors in compact online
  loops rather than replacing semantics with a closed controller;
- four-frame/delta context plus curated belief memory outperforms indiscriminate
  history accumulation;
- short plans must stop on the first contradictory/no-effect transition;
- progress and information gain must be traded against scarce action cost;
- single-run score changes are weak evidence because variance and sequential
  level cancellation are large;
- the useful separation is a broad research/abduction horizon and a narrow,
  grounded action-commit horizon.

Source synthesis: `/home/pauloabelha/reflector2/insights/kaggle/insights.md` and
`insights-notebooks.md`. These are research inputs, not empirical evidence that
any proposed R2 change will improve score.

## Initial diagnosed seam

The live AR25 trace shows that Qwen can express a plausible FIT hypothesis and
CAE can discover/refute moving assemblies, but the structured semantic protocol
privileges a fixed `FIT → fit_residual` mapping. Qwen cannot define a new
bounded concept or measurement such as a relation between occupied material and
structured negative space. R2 therefore receives the lexical conclusion without
the explanatory bridge that made it plausible.

The first intervention will not add “holes mean fit.” It will make existing
verbs/observables explicit priors and add a bounded, neutral semantic
measurement-proposal channel that R2 may compile or reject.
