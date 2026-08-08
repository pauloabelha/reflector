# ARC-AGI-3 public environments

This directory contains the 25 local public ARC-AGI-3 environment artifacts
used by the Reflector-II harness. They were copied without bytecode caches from
the local public bundle at:

```text
/home/pauloabelha/arc-agi-3-public-games-2026/environment_files
```

Each game retains the toolkit's versioned directory, `metadata.json`, and
Python environment source. No recordings, prior agent outputs, policies, or
Reflector-I code are included.

The `arc-agi` toolkit discovers these files recursively and replaces the
download-time `local_dir` metadata value with the actual directory containing
each `metadata.json` file.
