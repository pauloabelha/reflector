# Checkpoint 005: semantic context admission liveness

Time: 2026-08-12

## Failure

A no-code-change CD82 transfer run reached turn 9, then failed before model
transport. Even the exact mandatory dependency closure required 16,678 tokens
including the protected 2,048-token output reserve, exceeding Qwen's 16,384
context window by 294 tokens.

The semantic request contained the same prior working state three ways: the
top-level exact `model_scratchpad`, a scratchpad copy inside
`prior_working_note`, and the entire prior note again under
`scratchpad_context.qwen_note`.

## Repair

New turns carry one exact model scratchpad. The compact prior projection keeps
the structured proposal, alias/evidence, question, citation, transition-basis,
and consolidation fields needed for revision and validation. Action-evidence
validation reads that canonical projection while retaining compatibility with
old duplicated replays. No graph evidence, current R2 projection, transition,
visual causal unit, output reserve, or admission check was removed.

## Evidence

- The partial repair reduced the live overflow from 294 to 50 tokens.
- The complete repair reduced a representative late request envelope from
  47,964 to 44,812 bytes.
- The exact CD82 rerun admitted and completed Qwen call 10, settled action 10,
  and began call 11; the prior build crashed forming the turn-9 request.
- 86 focused tests pass.
- The full suite has 240 passes and one unchanged missing historical artifact.

This verifies semantic-loop liveness at the reproduced boundary. It does not
show level completion, better control, or score improvement.
