# Frozen multi-effect cross-game gate v1

Metadata-only hash selection fixes `tu93-0768757b` before frame inspection.
The dispatcher contains exactly two previously earned effect classes:
translation-grounded affordance exploration (commit `5bfbf95`) and localized
substitution/selection symbolic induction (commit `47d8de9`).  It calibrates
simple opaque actions, selects a class only from transition structure, and
otherwise abstains.  No target substitution or in-version repair is allowed.

PASS requires level 1 within 24 total actions and exact replay.  This target
has prior public-census exposure, so the result is a fresh cross-game mechanism
test rather than pristine hidden-game evidence.
