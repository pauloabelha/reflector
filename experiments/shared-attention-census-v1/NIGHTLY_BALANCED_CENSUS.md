# Nightly balanced public-suite census

This run executes the authoritative amendment at the top of `PROPOSAL.md`.

## Why breadth now

The ar25 sequence has already localized the architecture's major interfaces:
shared residency works, structured criticism reaches Qwen, and a Qwen schema
can cross R2's cutoff and ground uniquely. Its final grounding was likely
semantically wrong and never influenced control. More ar25-specific iteration
would risk optimizing the interface around one known game. The public suite is
now the better instrument for discovering whether useful pickup occurs
naturally elsewhere.

The broad run was previously blocked by infrastructure, not scientific risk:
v1.3 needed roughly 58 minutes for one 25-action pair because about 10,000 graph
events per arm were fsynced separately. Transactional graph batches preserve
the exact ordered event stream while a 300-event benchmark improved from
2.4973 seconds / 300 outer commits to 0.0098 seconds / one commit. A preserved
9,904-event graph round-tripped exactly from one batch.

## Frozen matrix

- 25 public games × 2 fresh arms = 50 jobs.
- One `balanced` profile only; no sensitivity sweep tonight.
- 32 actions/job; Qwen at 0, 8, 16 only.
- Four environment threads; one FIFO resident GPU model.
- Maximum 75 Qwen calls.
- Every action and cognition transaction is checkpointed; every completed arm
  receives a fresh environment replay.

## Measurements

The census records author/provenance, support and attention, frontier exposure,
grounded pickup in both directions, schema/explanation novelty, bindings,
predictions, evidence, action influence, level progress, tokens, latency,
context occupancy, replay, failures, and paired deltas. Results are classified
into A/B/C/D plus HARMFUL and INVALID exactly as defined in the main proposal.

## Operational verdict

The run may reveal that some games exceed the frozen exact context. Those jobs
remain valuable feasibility measurements but cannot enter paired cognitive or
score claims. Independent failures do not erase unrelated games. Global
epistemic-integrity failures stop the matrix.

No held-out observation may change this run's code or configuration. Any repair
creates a new version and a new fresh matrix.

