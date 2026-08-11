# Parallel Cognitive Workspace v1.12

v1.12 is the fresh replacement for the context-invalid but mechanistically
positive v1.11 run. It retains v1.11's paired ar25 test, 64-action budget,
sources `0,8,16,24`, typed 4+1 probes, 24,576 context, environment-only support,
checkpoint/replay gates, and strict causal PASS criterion.

It changes only the causal revision interface:

1. The authoritative graph remains exact and replayable, but a revision turn
   renders one versioned, semantically lossless causal packet instead of
   recursively retransmitting the same canonical dependency closure. The
   packet preserves all live alternatives, all selected prediction judgments
   including unresolved outcomes, target/derivation/criticism ancestry,
   complete grounding, relation facts, and stable addresses/digests.
2. Exact action-free temporal relations observed in the tested transition are
   part of the complete grounding view, with before/after frame-digest
   provenance. This lets the same predicates R2 observed be mechanically
   validated if Qwen uses them.
3. On a revision turn Qwen can emit exactly one evidence-citing schema revision
   or explicit abstention. Explanations, attention, expansions, and competing
   alternatives are unavailable in that response.
4. The completion maximum/reserve rises globally from 2,048 to 3,072 tokens;
   context size, call count, model, temperature, and all semantic vocabularies
   remain unchanged.

The packet is lossless for its explicitly versioned causal-revision fields;
canonical graph objects remain externally addressable authority. It does not
claim byte-for-byte reconstruction of the entire graph from the prompt.

No prior schema, Qwen response, notes, solution trace, action meaning, or prior
workspace may enter a fresh v1.12 arm. Preserved v1.11 artifacts are offline
codec/compiler fixtures only.
