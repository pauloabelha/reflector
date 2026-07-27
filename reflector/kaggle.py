"""Build and verify the self-contained Kaggle submission overlay."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY_FILES = (
    "reflector/__init__.py",
    "reflector/symbolic.py",
    "reflector/perception.py",
    "reflector/schemas.py",
    "reflector/mind.py",
    "reflector/policy.py",
    "reflector/trace.py",
    "agents/templates/reflector_agent.py",
    "agents/__init__.py",
)


def build_overlay() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in OVERLAY_FILES:
            archive.write(ROOT / relative, relative)
    return buffer.getvalue()


def export_submission(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay = build_overlay()
    zip_path = output_dir / "reflector-kaggle-overlay.zip"
    zip_path.write_bytes(overlay)
    notebook_path = output_dir / "reflector-kaggle-submission.ipynb"
    notebook_path.write_text(
        json.dumps(_notebook(base64.b64encode(overlay).decode("ascii")), indent=2),
        encoding="utf-8",
    )
    return zip_path, notebook_path


def _notebook(encoded_overlay: str) -> dict[str, object]:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Reflector: symbolic ARC-AGI-3 baseline\n",
                "Generated from the official ARC-AGI-3 Agents starter contract.",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "%pip install --no-index --find-links "
                "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/"
                "arc_agi_3_wheels arc-agi python-dotenv"
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": _submission_cell(encoded_overlay),
        },
    ]
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "cells": cells,
    }


def _submission_cell(encoded_overlay: str) -> list[str]:
    source = f'''import base64
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

working = Path("/kaggle/working")
starter = working / "ARC-AGI-3-Agents"
if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
    subprocess.run(
        ["curl", "--fail", "--retry", "999", "--retry-all-errors",
         "--retry-delay", "5", "--retry-max-time", "600",
         "http://gateway:8001/api/games"],
        check=True,
    )
    shutil.copytree(
        "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents",
        starter,
        dirs_exist_ok=True,
    )
    overlay = working / "reflector-kaggle-overlay.zip"
    overlay.write_bytes(base64.b64decode("{encoded_overlay}"))
    with zipfile.ZipFile(overlay) as archive:
        archive.extractall(starter)
    (starter / ".env").write_text(
        "SCHEME=http\\nHOST=gateway\\nPORT=8001\\n"
        "ARC_API_KEY=reflector-offline\\n"
        "ARC_BASE_URL=http://gateway:8001/\\n"
        "OPERATION_MODE=online\\nENVIRONMENTS_DIR=\\n"
        "RECORDINGS_DIR=/kaggle/working/server_recording\\n"
    )
    subprocess.run(
        [sys.executable, "main.py", "--agent", "reflector"],
        cwd=starter,
        env={{**os.environ, "MPLBACKEND": "agg"}},
        check=True,
    )
else:
    import pandas as pd
    pd.DataFrame(
        [["1_0", "1", True, 1]],
        columns=["row_id", "game_id", "end_of_game", "score"],
    ).to_parquet(working / "submission.parquet", index=False)
'''
    return source.splitlines(keepends=True)


def smoke_test() -> None:
    with tempfile.TemporaryDirectory(prefix="reflector-kaggle-smoke-") as raw:
        clean = Path(raw)
        starter = clean / "ARC-AGI-3-Agents"
        shutil.copytree(ROOT / "agents", starter / "agents")
        shutil.copy2(ROOT / "main.py", starter / "main.py")
        with zipfile.ZipFile(io.BytesIO(build_overlay())) as archive:
            archive.extractall(starter)
        environments = clean / "environment_files"
        shutil.copytree(
            ROOT / "tests" / "fixtures" / "official_toolkit" / "bt11",
            environments / "bt11",
        )
        probe = clean / "kaggle_probe.py"
        shutil.copy2(ROOT / "reflector" / "kaggle_probe.py", probe)
        command = [
            "unshare",
            "-Urn",
            sys.executable,
            str(probe),
            str(environments),
        ]
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(starter),
            "MPLBACKEND": "agg",
            "MPLCONFIGDIR": str(clean / "matplotlib"),
            "XDG_CONFIG_HOME": str(clean / "config"),
        }
        result = subprocess.run(
            command,
            cwd=starter,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode:
            raise RuntimeError(
                f"Kaggle smoke test failed ({result.returncode})\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        print(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(prog="reflector-kaggle")
    subcommands = parser.add_subparsers(dest="command", required=True)
    export = subcommands.add_parser("export")
    export.add_argument("--output", type=Path, default=ROOT / "dist")
    subcommands.add_parser("smoke-test")
    args = parser.parse_args()
    if args.command == "export":
        paths = export_submission(args.output)
        print("\n".join(str(path) for path in paths))
    else:
        smoke_test()


if __name__ == "__main__":
    main()
