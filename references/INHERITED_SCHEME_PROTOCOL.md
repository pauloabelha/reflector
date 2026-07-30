# Inherited scheme protocol

This protocol turns cross-run “common sense” into auditable symbolic artifacts
without putting an LLM or development service in ARC-AGI-3 inference.

## Separation of responsibilities

The deployed agent receives one immutable `SchemeLibrary` snapshot through its
serialized `MindConfig`. Each `SchemeDefinition` contains typed parameters,
grounding requirements, preconditions, effects, invariants, goal contracts,
dependencies, composition rules, falsifiers, resource bounds, and description
cost. Its SHA-256 content hash is its stable identity. The library root is a
Merkle-style hash of its sorted definition hashes.

Evidence is not part of a definition. Development maintains an append-only
`SchemeEvidenceLedger` keyed by definition hash. This allows independently
running agents to recognize the same operation while retaining distinct
confirmations and counterexamples. It also prevents confidence updates from
silently changing a scheme's meaning.

The offline LLM meta-critic may inspect cognitive streams and propose code or
typed scheme mutations between runs. It is not imported by the Kaggle overlay
and cannot act during an episode.

## Development cycle

1. Freeze a parent candidate, source fingerprint, games, budgets, prediction,
   and falsifier.
2. Run isolated diverse offspring and retain their immutable reports and
   cognitive streams.
3. Convert only preregistered prediction assessments into evidence events.
4. Assimilate a definition unchanged when its predictions transfer.
5. Accommodate the smallest falsified dependency into a new definition hash;
   preserve the parent and counterexample.
6. Reflect recurring coordinated dependencies into a higher-order definition.
7. Merge libraries by content hash. Merge ledgers by evidence-event hash.
8. Permit cultural inheritance only with repeated confirmation, at least one
   held-out confirmation, pragmatic progress, zero recorded regressions, and
   complete dependency closure.
9. Embed the exact selected snapshot into the offspring's `MindConfig`.
10. Apply the normal target, preservation, full-suite, export, and
    network-disabled Kaggle gates.

`evidence_from_cognitive_events` enforces the bridge from streamed cognition
to the ledger. It accepts only assessments with a preregistered hypothesis,
an inherited component present in the candidate's exact library, and a
definition-specific effect or externally observable goal contract. Generic
active priors cannot inherit credit from coincidental progress.

`breed_inherited_candidate` unions isolated ledgers by evidence hash, applies
the held-out gate, closes promoted definitions over their dependencies,
retains the parent's previously inherited library, and embeds the result in a
new candidate identity. This is the cultural exchange boundary between
offspring; episode bindings and unrestricted cognitive prose do not cross it.

## Evidence boundaries

An evidence event records a candidate, evaluation partition, episode digest,
preregistered prediction digest, outcome, and intervention savings. It does
not grant credit merely for perceptual novelty or a more elaborate trace.

The default cultural gate requires:

- at least two confirmed predictions;
- at least one confirmation in a partition named `heldout:*`;
- at least one level-progress event;
- zero prediction falsifications;
- zero regressions.

Dependencies of an accepted higher-order scheme remain in the exported
library even when they do not independently clear the higher-order promotion
gate.

## Leakage controls

Definitions must not contain game identifiers, fixed coordinates, action
routes, rendered colors, expected level counts, or hidden evaluation data.
Episode-specific bindings remain ontogenetic state and are not inherited.
Evidence partitions describe the evaluation role rather than becoming runtime
preconditions.

The candidate identity includes the full canonical library snapshot. A changed
definition therefore creates a changed scheme hash, library root, config,
candidate identity, and exported notebook genome.

## Current empirical status

The substrate is implemented and structurally validated. V53a carried six
content-free definitions through the official `r11l` harness, reproduced the
accepted level at action 18, grounded three applicable hashes into 390
transition assessments, passed the network-disabled Kaggle smoke, and exported
the exact library-bearing genome. Compiling that real stream produced zero
cultural evidence events, as required, because the generic starter forms make
no effect or goal prediction. This proves faithful transport, operative
grounding, and anti-hitchhiking—not task improvement. No inherited library
offspring is accepted until a definition with a risky contract passes real
held-out and preservation gates.
