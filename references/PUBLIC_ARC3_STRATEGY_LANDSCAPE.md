# Public ARC-AGI-3 strategy landscape

## Scope and conclusion

This note records public evidence available through 30 July 2026. It separates
official hidden-evaluation results from self-reported public-game results and
uses **purely symbolic** to mean that no neural model or LLM participates in
perception, hypothesis proposal, ranking, or action selection at inference
time.

The defensible conclusion is:

> Purely algorithmic ARC-AGI-3 agents exist, but there is no public evidence
> yet of a strong end-to-end pure-symbolic ARC-AGI-3 peer that jointly induces
> semantic objects, action affordances, transition laws, goals, and plans in
> the way Reflector attempts to do.

The nearest pure ARC-AGI-3 systems are graph-frontier explorers. The nearest
semantic precedents are pure-symbolic solvers for static ARC and causal-rule
learners for already-symbolized sequences. Most high-scoring current public
ARC-AGI-3 systems instead use an LLM to invent an explicit program or world
model, then use symbolic replay verification and planning.

This is a negative literature finding, not a proof that no unpublished or
undiscovered peer exists.

## Taxonomy of public ARC-AGI-3 approaches

| Family | Public examples | Inference mechanism | Classification and evidence |
| --- | --- | --- | --- |
| Exact-frame graph exploration | [Explore It Till You Solve It](https://github.com/dolphin-in-a-coma/arc-agi-3-just-explore) | Connected-component action proposals, processed-frame hashes, a directed transition graph, and shortest paths to untested state-action pairs | Purely algorithmic. The [paper](https://arxiv.org/abs/2512.24156) reports training-free graph exploration, not learned dynamics or semantic rule induction. |
| Object-weighted stochastic exploration | [GuidedRandomAgent](https://github.com/GameDevGitHub/GuidedRandomAgent) | Handwritten object tracking, action-type and object-click weights, no-op memory, and stochastic selection | Purely algorithmic, but heuristic rather than an explicit causal world model. |
| Learned affordance exploration | [StochasticGoose](https://github.com/DriesSmit/ARC3-solution) | An online CNN predicts which action or click is likely to change the frame | Neural, not symbolic. |
| Graph plus learned value | [Blind Squirrel](https://github.com/wd13ca/ARC-AGI-3-Agents) | Explicit state graph and rule-based action pruning plus a ResNet-18 state-action value model | Hybrid neuro-symbolic. |
| DSL plus LLM | [Fluxonian](https://github.com/FluxonApps/arc-prize-v3-2025) | Conditions, actions, rules, and persistent DSL programs, with an LLM agent used to construct or revise rules | Symbolic substrate, but not a pure-symbolic end-to-end agent. |
| LLM-generated executable world model | [Executable World Models](https://github.com/astroseger/arc-3-agents-baseline1), [Schema](https://schema-harness.github.io/) | A coding model writes a state representation, transition program, and goal test; exact replay certifies the model; BFS or another planner searches inside it | The learned proposal engine is an LLM. The resulting model, verifier, and planner are symbolic. |
| LLM multi-agent or REPL harness | [Arcgentica](https://github.com/symbolica-ai/ARC-AGI-3-Agents/blob/symbolica/arcgentica/SYMBOLICA_README.md), [Duck](https://github.com/Tufalabs/duck-harness), [Play Zero](https://github.com/dhanaabhirajk/ARC-AGI-3-Agents) | LLM roles, executable analysis code, visual prompting, or video analysis propose hypotheses and actions | LLM agents, even when they produce code or explicit theories. “Symbolica” is a company name, not evidence that Arcgentica is pure symbolic. |
| Public-set scripts, caches, or vulnerabilities | [Explore Before You Solve](https://arxiv.org/abs/2605.25931) documents repeated-action solutions and a null-coordinate issue | Fixed trajectories, exhaustive offline reachability, or benchmark-specific behavior | Useful benchmark audit, but not evidence of general rule induction. |

The [official Preview recap](https://arcprize.org/blog/arc-agi-3-preview-30-day-learnings)
provides the cleanest hidden-game comparison:

| Agent | Official Preview category | Score | Levels | Games | Actions |
| --- | --- | ---: | ---: | ---: | ---: |
| StochasticGoose | Smart Random (CNN) | 12.58% | 18 | 2 | 255,964 |
| Blind Squirrel | Smart Random (Rules) | 6.71% | 13 | 1 | 109,108 |
| Explore It Till You Solve It | Smart Random (Frame Graph) | 3.64% | 12 | 0 | 278,158 |
| GuidedRandomAgent | Smart Random (Rules) | 2.24% | 11 | 1 | 39,881 |
| Fluxonian | DSL + LLM | 8.04% | 5 | 0 | 11,890 |
| Play Zero | Random + LLM Video | 4.37% | 5 | 0 | 7,226 |

These results establish that neural inference is not required for nontrivial
hidden-game progress. They do not establish that graph exploration has learned
the mechanics: the official recap explicitly says some Preview games were too
friendly to brute force and treats action efficiency as the important
intelligence signal.

## Pure-symbolic precedents outside interactive ARC-AGI-3

Several systems are philosophically close to parts of Reflector, but none must
solve the complete ARC-AGI-3 induction problem.

### Static ARC

- [Icecuber's 2020 ARC solution](https://github.com/top-quarks/ARC-solution)
  performs deterministic enumerative search over shallow compositions from a
  large hand-built transformation library. It is a genuine pure-symbolic
  runtime and won the 2020 Kaggle challenge, but static ARC supplies
  input/output examples and therefore supplies the target behavior.
- [ARGA](https://arxiv.org/abs/2210.09880) constructs object-centric graph
  abstractions and searches a DSL using constraint acquisition, state hashing,
  and Tabu search. It is the closest static precedent for object predicates
  plus explicit transformation-program search.
- [GPAR](https://arxiv.org/abs/2401.07426) casts object-centric ARC tasks as
  PDDL generalized-planning problems and synthesizes pointer-based planning
  programs.
- [Descriptive Grid Models with MDL](https://arxiv.org/abs/2112.00848) searches
  for intelligible parse/generation models using formal description length.
  Its published system solved 29 of 400 ARC training tasks at 30 seconds per
  task, illustrating both the value and the coverage limit of a compact model
  language.
- [ARC program synthesis with ILP](https://arxiv.org/abs/2405.06399) induces
  logic programs over a hand-written object-centric DSL. Its experiments
  deliberately select tasks covered by the implemented primitives, making the
  language-coverage dependency explicit.

### Causal and game-rule induction

- The [Apperception Engine](https://arxiv.org/abs/1910.02227) and its
  [implementation](https://github.com/RichardEvans/apperception) synthesize a
  lowest-cost symbolic causal theory of objects, properties, laws, and unity
  constraints from short sensory sequences. This is a close precedent for
  interpretable causal-theory induction, but the original system consumes
  already-symbolized observations rather than ARC-AGI-3 pixels.
- [Inductive General Game Playing](https://arxiv.org/abs/1906.09627) asks ILP
  systems to recover logic-game rules from traces. Even after perception and
  active experiment selection are removed, the best evaluated ILP system
  perfectly learned only 40% of the tasks.

These precedents show that pure symbolic induction is a real research family,
not an idiosyncrasy of Reflector. They also expose why static-ARC success does
not transfer automatically: ARC-AGI-3 withholds the desired output, requires
costly information-gathering actions, and asks the agent to infer the goal as
well as the transition law.

## What the current field says: the proposal problem

The recurring bottleneck is not executing or searching a correct symbolic
model. It is proposing the right representation and law from sparse
interaction.

1. **Grounding is underdetermined.** Connected components can be objects,
   decorations, counters, animation fragments, or pieces of a larger object.
   Several incompatible parses can explain the same early transitions.
2. **The vocabulary bounds the solution.** If a DSL lacks the true relation,
   latent variable, or operation, exhaustive search cannot recover it.
   Expanding the language then expands the combinatorial search.
3. **ARC-AGI-3 couples four searches.** The agent must infer a perceptual parse,
   action grounding, transition program, and goal predicate at the same time.
4. **Sparse traces admit many consistent theories.** Efficient progress
   requires interventions selected to distinguish hypotheses, not only novel
   frames or actions likely to produce visible change.
5. **Exact models are brittle to observation noise.** Status displays,
   animation phases, and transient effects can turn one causal state into many
   raw frames or falsify an otherwise correct deterministic model.

LLMs currently act as broad learned proposal distributions over
representations and programs. The symbolic components then provide
falsifiability and cheap planning:

- [Executable World Models](https://arxiv.org/abs/2605.05138) has a coding
  agent maintain Python state and transition programs, replay observations,
  simplify the model, and plan before acting.
- Its [component ablation](https://arxiv.org/abs/2607.15439) found that stronger
  models and greater reasoning effort improved every agent variant; exact
  verification ranked first in all tested model-effort settings, but variant
  differences were smaller than model and effort effects.
- [Schema](https://schema-harness.github.io/) enforces the same core loop:
  jointly edit state grounding and `step`, replay every recorded transition,
  search inside the certified program, and abort an action queue on prediction
  mismatch.

This convergence supports Reflector's use of explicit causal state, executable
rules, verification, and planning. It does **not** demonstrate a pure-symbolic
solution to open-ended hypothesis proposal because an LLM performs that step.

## Score comparability and evidence limits

Public numbers belong to different regimes and must not be directly ranked.

- The 2025 Preview used three hidden private games and a different game set and
  budget from the 2026 competition.
- The current 25 downloadable games are public development material. Repeated
  runs, best-of-\(n\), public-game traces, newer models, and development against
  those games can all raise self-reported scores without measuring hidden
  transfer.
- [Arcgentica's 36.08%](https://www.symbolica.ai/blog/arc-agi-3) is explicitly
  an unverified score on the 25 public games.
- The [Executable World Models repository](https://github.com/astroseger/arc-3-agents-baseline1)
  reports about 99% with GPT-5.6 Sol but explicitly labels the result
  public-set saturation and says held-out performance is untested.
- Schema reports 98.98% and 95.35% on the public set and explicitly labels both
  results self-reported. It releases [run traces](https://huggingface.co/datasets/schema-harness/arc-agi-3-schema-traces/tree/main),
  but not an official private evaluation.
- The [ARC-AGI-3 paper](https://arxiv.org/abs/2603.24621) defines the intended
  problem as exploration, goal inference, internal modeling, and planning on
  novel environments. The [2026 competition](https://arcprize.org/competitions/2026/arc-agi-3)
  uses unseen games; that evaluation, not saturation of the known 25, is the
  relevant generalization test.

For Reflector, local public-development score, Kaggle public-leaderboard score,
and Kaggle private-leaderboard score must remain separate. Scores also require
the game inventory, source commit, action budget, reset/memory policy, run
count, and official/self-reported status. The paired protocol in
[SYMBOLIC_ARC3_COMPARISON.md](SYMBOLIC_ARC3_COMPARISON.md) is the appropriate
local standard.

## Pure-symbolic implications for Reflector

The public evidence suggests strengthening symbolic proposal and experiment
selection rather than abandoning the symbolic architecture.

1. **Retain an exact graph-frontier fallback.** It provides bounded systematic
   coverage and useful traces when no semantic theory is ready. Its state key
   should be a nuisance-reduced causal abstraction, not merely a raw frame
   hash.
2. **Represent a version space, not one story.** Maintain competing hypotheses
   over perceptual parses, affordances, latent state, transition programs, and
   goal predicates until an observation distinguishes them.
3. **Select discriminating probes.** Rank legal actions by expected eliminated
   hypothesis mass per action cost, including predicted no-ops and invalid
   effects as informative outcomes.
4. **Use counterexample-guided inductive synthesis.** Enumerate the
   minimum-description candidate, replay all prior transitions exactly, retain
   the pointed counterexample, and refine the grammar or program.
5. **Make the simplicity prior explicit.** Score parse cost, program cost,
   reusable-library cost, and unexplained residual separately. An ad hoc
   confidence is not an MDL substitute.
6. **Learn a symbolic library across games.** Anti-unify validated programs and
   promote typed macros only when held-out evidence pays for their complexity.
   This supplies part of the reusable proposal prior that neural systems get
   from pretraining.
7. **Separate latent state from observation.** Model status bars, animation,
   occlusion, and delayed visual effects as an observation function over a
   stable causal state.
8. **Preserve all negative evidence.** No-ops, illegal actions, loops, and
   prediction failures constrain the theory as strongly as visible changes.
9. **Certify plans through replay.** A proposed transition law should reproduce
   the complete append-only trace before it controls multi-action execution;
   invalidate the remaining plan on the first mismatch.
10. **Test transfer, not recognition.** Freeze the exact source and evaluate on
    hidden games and procedural mutations. Improvements confined to named
    public-game structures are engineering diagnostics, not evidence of a
    general symbolic proposal mechanism.

The safe project-level claim is therefore:

> Reflector pursues an unusually strict end-to-end pure-symbolic form of an
> architecture the ARC-AGI-3 field increasingly uses: explicit state,
> executable dynamics, exact verification, and planning. Its distinctive
> unsolved problem is replacing the LLM proposal prior with bounded,
> evidence-driven symbolic construction.
