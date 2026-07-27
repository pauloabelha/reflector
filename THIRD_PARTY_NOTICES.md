# Third-party notices

Reflector began from the official
[`arcprize/ARC-AGI-3-Agents`](https://github.com/arcprize/ARC-AGI-3-Agents)
starter. Retained and adapted starter files, principally `agents/`, `main.py`,
and starter configuration, are Copyright 2025 ARC Prize and MIT licensed. The
exact audited upstream revision is recorded in [KAGGLE.md](KAGGLE.md).

The Kaggle inference artifact relies on the competition-provided packages:

| Component | Source | License |
| --- | --- | --- |
| ARC-AGI-3 Agents starter | `arcprize/ARC-AGI-3-Agents` | MIT |
| `arc-agi` / `arcengine` | `arcprize/ARC-AGI` | MIT |
| `python-dotenv` | `theskumar/python-dotenv` | BSD-3-Clause |

Those packages are installed from the official competition data mount during
the offline notebook run. They are not vendored into Reflector's inference
overlay. Their copyright notices and license texts remain authoritative.

Development dependencies and optional starter templates are outside the
submitted inference closure. A winning release must still archive the exact
lockfiles, notebook, source commit, competition data version, and notices used
for the selected Kaggle submission.
