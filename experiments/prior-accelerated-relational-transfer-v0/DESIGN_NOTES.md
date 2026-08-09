# Design notes

The experiment reuses `reflector2.perception.perceive_grid` for the canonical
R2 structural witness and the public ARC toolkit transport conventions from
`reflector2.arc_harness`. It does not duplicate or replace the core graph,
explanation engine, or transition learner.

The experiment-local learner exists because `Runtime.learn_transition`
currently chooses the first region correspondence. The hypothesis here needs
a joint consequence over several same-outline figures. The local layer reads
ordinary frame geometry only to compute correspondence and displacement; its
schema atoms retain existing `SameOutline` and compose existing figure/cell
facts into palette-invariant `SameInteriorLayout` / `DifferentInteriorLayout`
relations plus generic `Decrease`/`Preserve` effects. This refinement matters:
the coarse `InteriorContrastCount` gives spatially distinct interiors the same
count. No object receives a semantic role such as player, key, or target.

The controller separates three things that are easy to accidentally conflate:

1. a source-derived action-agnostic schema and its real source evidence;
2. an external action-agnostic proposal with zero empirical evidence;
3. a target-local opaque-action consequence learned after acting.

The target-local attachment is stored as a child record carrying both parent
provenance and local confirmation. It is not exported back into either parent.

Target selection is performed by the same R2 perception facts used for
binding. Game IDs are transport/report labels only. The negative target forces
the key null behavior: a structurally irrelevant prior must abstain, producing
the same action sequence as scratch.
