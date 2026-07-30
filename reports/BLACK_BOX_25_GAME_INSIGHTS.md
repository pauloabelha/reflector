# Black-box ASCII play: 25-game mechanism survey

Date: 2026-07-30

## Evidence boundary

Every public-development game was opened through the official offline wrapper.
The diagnostic player used only rendered frames, legal action IDs, action
outcomes, state, and completed-level count. It did not inspect any game
implementation. Frames were converted to modal-block ASCII with explicit
value legends; every action records changed-pixel count, bounding box, and
value-transition histogram.

The complete JSON and Markdown traces are archived in
[`black-box-ascii-survey-v69.tar.gz`](black-box-ascii-survey-v69.tar.gz)
(SHA-256
`954bf98ff0040c135ec0c73a3005e1af7ba7d334a08247408abfbed5465ad78d`).

The first pass applied every legal non-coordinate control once, then clicked
the smallest, median, and largest non-background connected components when a
coordinate action was legal. A second visual pass probed additional enclosed
cells, isolated tokens, track endpoints, and target-like clusters in the most
ambiguous click-only scenes. Coordinates belong only to these diagnostic
traces and are not eligible for runtime code or inherited knowledge.

The “needed mechanism” column is an evidence-ranked hypothesis, not a decoded
game rule.

## Per-game observations

| Game | Black-box evidence | Generalizable mechanism apparently needed |
| --- | --- | --- |
| `ar25` | Four controls caused reversible 109-pixel transformations; another control changed one apparent status pixel. V69 already reaches 2/8. | Bind controls to transformations of persistent relational objects, then plan a multi-step global relation rather than optimize raw pixel mismatch. |
| `bp35` | Three plain controls repeatedly moved a 47-pixel interior structure; generic clicks changed only an edge counter. | Factor navigation from interaction mode, suppress status-layer changes, and search for a grounded click affordance conditional on agent pose. |
| `cd82` | Directional controls moved an outlined pose template; apply committed a half-plane layer; palette clicks changed the active attribute. | Constructive programs over `SelectAttribute`, `NavigatePose`, and repeated `ApplyLayer`; later levels require secondary-template masks and exact last-write-wins composition. |
| `cn04` | Plain controls transformed a 144–207-pixel object; one component click changed 279 pixels across two interior regions. | Learn mode-conditioned object selection and transport, with independent controller roles and exact relational before/after matching. |
| `dc22` | Four controls produced small reversible translations of an interior token; most click probes affected only status pixels. | Boundary-aware navigation plus relational target/contact induction; do not treat a no-effect click or edge counter as world dynamics. |
| `ft09` | Naive component clicks were inert, while the accepted trace solves all levels by clicking grounded lattice nodes. | Repeated-form lattice grounding, prospective binary effect induction, and exact constraint solving; generic component salience alone is insufficient. |
| `g50t` | Two controls were initially no-ops, one moved a 49-pixel structure, and another rewrote a 71-pixel local region. | Infer boundary-conditioned action semantics and phase-specific operators before planning toward a relational goal. |
| `ka59` | Four controls moved a compact token by small reversible effects; sampled clicks were inert or status-only. | Identify controllable object, obstacles, and target relation, then use shortest-path/contact planning with boundary-aware no-effect evidence. |
| `lf52` | Plain actions updated only a top-edge counter; one object click caused a 29-pixel structured interior rewrite. | Separate protocol feedback from task state and learn click affordances over coherent relational objects rather than balancing all action IDs. |
| `lp85` | Naive clicks were inert, but accepted traces expose conserved-token permutations and solve 5/8 levels. Level 6 exceeds the current 64-slot path domain. | Scalable permutation composition over larger or branching conserved structures, with topology-conditioned controller identity and bounded abstraction rather than a raised literal cap. |
| `ls20` | Four controls produced reversible 52-pixel translations of a composite lower-region object. | Persistent-object navigation with collision/topology inference and a grounded target predicate. |
| `m0r0` | Directional controls shifted paired 50-pixel strips; apply/click probes were mostly inert or status-only. | Multi-object contextual transitions and multi-phase goal procedures, not a single terminal contact heuristic. |
| `r11l` | One visually grounded click caused a 116-pixel scene restructuring; other sampled clicks only updated a counter. | Rank and bind the causally active object, infer a select/apply transformation, and derive the relational goal from the resulting structure. |
| `re86` | Four controls moved a roughly 60-pixel structure reversibly; a fifth changed only two sparse pixels. | Navigation/contact planning with action-role separation and explicit phase/terminal-gate induction. |
| `s5i5` | Broad component clicks were status-only; a visually chosen cell in an enclosed grid caused an 11-pixel interior rewrite. | Represent grids as cells/relations, learn sparse cell affordances, and synthesize a target transformation rather than click component centroids. |
| `sb26` | Generic probing found one 20-pixel component effect; the accepted planner solves 8/8 through a uniquely grounded finite connector problem. | When the grounded space is small, enumerate assignments completely, require a unique structural model, and execute an exact plan. |
| `sc25` | Plain controls produced distinct 8–36-pixel transformations; two clicks caused 13-pixel changes spanning a small interior object and status feedback. | Factor coupled controller families, identify mode/selection state, and jointly plan interacting objects. |
| `sk48` | One action pair transformed a 96-pixel region; another family transformed a separate 12-pixel object. | Discover independently controllable factors and search joint relational state instead of pooling effects by action family alone. |
| `sp80` | Controls moved structures at two scales (about 162 versus 34 pixels); later probes mostly consumed a status resource. | Multi-scale object/track representation, resource-aware long-horizon transport, and phase segmentation. |
| `su15` | A click on a visible endpoint and the non-coordinate control then produced related 16–23-pixel effects on the same small region. | Learn a selection/activation mode followed by an apply or move operator, preserving role identity across attribute changes. |
| `tn36` | Most clicks changed only a counter, but visually selected clue cells toggled three interior pixels on a regular board. | Suppress the feedback strip, ground repeated cells and clue relations, and actively learn a local cell-transition law before solving. |
| `tr87` | One action pair moved a 13-pixel object; the other moved a distinct 28-pixel object. | Factor action-to-object controllability and perform joint multi-object relational planning. |
| `tu93` | Three initial controls appeared status-only while a fourth caused a 19-pixel interior movement. | Treat no-effect evidence as pose/boundary conditioned, recover controller semantics through re-positioning, and infer the target relation. |
| `vc33` | Generic clicks were counter-only; a visually selected compact region caused a 265-pixel global restructuring. | Sparse affordance discovery over compact objects, causal hotspot prioritization, and exact phase/state abstraction after a productive click. |
| `wa30` | Four controls moved a 32-pixel object reversibly; the fifth changed only a status pixel. | Persistent-object navigation, collision/target inference, and nuisance-layer suppression. |

## Cross-game priors supported by the survey

These are candidates for a generic knowledge base. They must remain
falsifiable and may rank hypotheses, but cannot override current observations.

1. **Causal scene versus nuisance layer.** Repeated edge counters and status
   strips should be modeled separately from persistent task objects.
2. **Persistence and role identity.** Objects and controller roles usually
   persist through translation, recoloring, partial overwrite, and phase
   changes.
3. **Locality, sparsity, and conservation.** Prefer compact effects,
   conserved multisets, and local permutations until evidence demands a global
   rewrite.
4. **Equivariance.** Translation, recoloring, object order, and D4 transforms
   should not change a learned operator's identity.
5. **Boundary-conditioned no-effect.** An inert directional action can mean a
   blocked pose, not an invalid controller.
6. **Factored controllability.** Different action subsets may control
   different objects or modes; effects must not be pooled solely by action ID.
7. **Selection–application separation.** Attribute/object selection,
   navigation, apply/commit, and terminal checking are distinct candidate
   roles.
8. **Constructive intermediate states.** A useful program may temporarily
   increase pixel disagreement and may require multiple last-write-wins
   commits.
9. **Relational goals.** Contacts, correspondences, reference grids, markers,
   enclosures, and target slots are stronger goal candidates than arbitrary
   frame novelty.
10. **Exact bounded search.** Once a small transition system is causally
    verified, use CSP/BFS/enumeration rather than a greedy visual heuristic.
11. **Active causal experiments.** Prefer interventions that discriminate
    representation or transition hypotheses; repeated action coverage without
    a prospective prediction is weak evidence.
12. **Falsification and abstention.** Quarantine a prior on prospective
    conflict, and abstain when grounding is ambiguous or an action is not
    represented.

## Current measurement

The independently gated v69 policy scores **10.255448098096416/100** on all
25 public-development games, with 30/183 levels across 12 games and two games
fully complete. The black-box survey is diagnostic evidence and is not part of
that score.
