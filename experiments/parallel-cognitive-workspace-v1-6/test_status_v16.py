from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v16_status_tested", HERE / "experiment.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_diagnostic_witness_cannot_overwrite_live_status(monkeypatch) -> None:
    monkeypatch.setattr(
        MODULE,
        "_COMPILE_AMBIGUITY_WITNESS",
        lambda *_args, **_kwargs: {
            "status": "ambiguous-grounding",
            "candidate_substitutions": [],
        },
    )
    witness = MODULE.compile_ambiguity_witness(object(), {})
    merged = {**{"status": "ambiguous-active"}, **witness}
    assert merged["status"] == "ambiguous-active"
    assert "status" not in witness

