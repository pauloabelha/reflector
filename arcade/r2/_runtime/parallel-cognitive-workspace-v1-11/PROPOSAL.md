# Parallel Cognitive Workspace v1.11

v1.11 is a fresh replacement for the valid v1.10 failure. It changes only the
generic unbound-schema repair interface:

1. R2's bounded grounding witness includes condition-wise fact counts, isolated
   grounding counts, leave-one-condition-out grounding/effect-pair counts, and
   explicit blocking-condition indices.
2. The stable generic prompt tells Qwen to remove or replace a diagnosed
   blocking condition with a relation verified in the current relation set.
3. Evidence citation arrays are grammar-enforced as unique.
4. The same four calls move to sources `0,8,16,24`, so an unbound criticism
   committed when the first response integrates at action 8 is visible to an
   immediate repair turn. Logical release remains eight actions.

All other v1.10 choices and strict PASS/FAIL/INVALID gates remain unchanged:
fresh paired ar25, 64 actions, typed 4+1 probe budget, exact evidence return,
24,576 context, environment-only support, exact checkpoints/replay, no notes,
no frozen/external semantics, and no prior-run cognition.
