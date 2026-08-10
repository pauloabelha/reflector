"""Primary Reflector-II solver entry point backed by the proven v1.16 workspace.

The v1.16 implementation is intentionally loaded as one frozen chain.  It is
the implementation that completed a fresh paired ARC level with a durable
Qwen -> R2 -> environment -> Qwen -> R2 control trace.  New native components
may replace pieces of this chain only after behavioral equivalence is tested;
this entry point must never silently select an unproven rewrite.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence


PROVEN_PROTOCOL = "prospective-control-v1.16"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROVEN_EXPERIMENT = (
    REPOSITORY_ROOT
    / "experiments"
    / "parallel-cognitive-workspace-v1-16"
    / "experiment.py"
)
PROVEN_STATUS = PROVEN_EXPERIMENT.with_name("STATUS.md")


class ProvenWorkspaceUnavailable(RuntimeError):
    """The exact proven workspace implementation is not present."""


def load_proven_experiment() -> ModuleType:
    """Load the exact v1.16 experiment chain from this checkout."""

    if not PROVEN_EXPERIMENT.is_file():
        raise ProvenWorkspaceUnavailable(
            f"proven workspace is missing: {PROVEN_EXPERIMENT}"
        )
    module_name = "reflector2_proven_workspace_v116"
    existing = sys.modules.get(module_name)
    if isinstance(existing, ModuleType):
        return existing
    spec = importlib.util.spec_from_file_location(module_name, PROVEN_EXPERIMENT)
    if spec is None or spec.loader is None:
        raise ProvenWorkspaceUnavailable(
            f"cannot load proven workspace: {PROVEN_EXPERIMENT}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    config = module.load_config()
    if config.get("workspace_protocol") != PROVEN_PROTOCOL:
        raise ProvenWorkspaceUnavailable(
            "proven workspace protocol changed unexpectedly: "
            f"{config.get('workspace_protocol')!r}"
        )
    return module


def verified_result_available() -> bool:
    """Return whether the checked-in evidence record declares the fresh PASS."""

    if not PROVEN_STATUS.is_file():
        return False
    status = PROVEN_STATUS.read_text(encoding="utf-8")
    return (
        "fresh paired result: PASS" in status
        and "shared_live_qwen" in status
        and "levels=1, actions=38" in status
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the proven shared-workspace solver/census coordinator."""

    module = load_proven_experiment()
    return int(module.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
