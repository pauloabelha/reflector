# Blind-panel contamination incident

Incident date: 2026-08-03.

Before any development, validation, or blind condition run, a developer
stress-test mistakenly iterated over every pair listed in the base
preregistration. It instantiated blind seeds 3101–3108 in memory and printed
their latent action transitions while checking visual-template grounding.

Consequences:

- blind-01 through blind-08 are permanently excluded from scientific results;
- no score, condition comparison, Mind adaptation, or artifact was produced on
  those pairs;
- the base preregistration remains immutable and its SHA-256 remains valid;
- the replacement panel in `blind_panel_amendment.json` was frozen before any
  replacement instance was generated or inspected;
- the aggregate criterion, controls, panel size, same-k definition, weights,
  budgets, and tie policy are unchanged;
- any run using the contaminated seeds must be marked inconclusive by the panel
  runner.

This incident is part of the permanent experiment record. It must be surfaced
in the final report rather than silently omitted.
