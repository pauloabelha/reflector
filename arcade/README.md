# Reflector-II human arcade

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
