# Open-source AI disclosure

Audit date: 2026-07-27.

This disclosure maps Reflector to the Open Source AI Definition 1.0 checklist
referenced by the ARC-AGI-3 competition rules.

## System

Reflector is a deterministic symbolic AI system. Its preferred form for
modification is this repository's Python source, TypeScript analysis source,
configuration schema, tests, lockfiles, and generated Kaggle notebook. The
submitted inference closure is enumerated by `reflector.kaggle.OVERLAY_FILES`
and tested automatically.

The system grants permission to use, study, modify, and share
Reflector-authored material under MIT-0 or CC BY 4.0. Retained official starter
material remains MIT licensed. See [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Model and parameters

There is no neural model, pretrained model, checkpoint, hidden prompt, or
weight tensor in the Reflector submission. The operative model consists of:

- the symbolic perception, schema, causal, abstraction, and planning source;
- a complete `MindConfig` JSON genome embedded in the submitted notebook;
- symbolic state learned online from observations during the evaluation run.

Consequently, “open weights” is not an omitted artifact: no weights exist.
Every parameter is named in `MindConfig`, serialized as JSON, and directly
exportable with `reflector-kaggle export --config`.

## Data information

The baseline performs no offline training. It does not derive model parameters
from private, proprietary, or unlisted training data. Its only runtime inputs
are observations supplied by the ARC-AGI-3 evaluation gateway.

Development evaluation uses:

- public ARC-AGI-3 environments distributed by the competition;
- the deterministic `bt11` fixture retained from the official toolkit;
- deterministic transformations of recorded public traces, with seeds stored
  in experiment manifests.

Competition data is not redistributed from this repository. Its source,
version, license, transformations, and experiment hashes must be recorded for
any reported result. If an optional LLM mutation provider is used during
development, that provenance must be disclosed; the provider and LLM are not
part of Kaggle inference. The recommended prize submission uses only
deterministic mutation unless a separately documented, reasonably accessible,
open system is selected.

## Reproducibility

The source commit, `uv.lock`, `web/package-lock.json`, candidate JSON,
generated notebook, overlay hash, experiment manifests, scorecard, and traces
form the release record. `kaggle_smoke_test` executes the inference artifact in
a fresh network namespace. `reflector-prize-audit` checks the static prize
contract, while an actual committed Kaggle rerun remains the authoritative
competition test.
