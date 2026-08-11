# Reflector-II arcade

This package contains two loopback-only surfaces:

- `python -m arcade` starts the human controller.
- `python -m reflector2.r2 --arcade` starts the Agent Arcade view of the
  current canonical R2 runtime.

`arcade/` contains presentation and replay code, not the model backend or agent
policy. R2 model profiles, OpenAI setup, budgets, and Kaggle usage are
documented in [`src/reflector2/r2/README.md`](../src/reflector2/r2/README.md).

## Human controller

This is the copied local ARC-AGI-3 human controller and its note journal.
It deliberately executes only actions chosen in the browser; it is not an
agent policy.

Run from the repository root:

```bash
PYTHONPATH=. python3 -m arcade
```

Or, after installing the project, run `reflector2-arcade`.

The existing observations are in `notes.json`. New notes append to that file
by default. Use `--notes-path /path/to/journal.json` to work in a separate
journal without changing the copied record.
