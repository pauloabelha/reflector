from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v15_transport_tested", HERE / "experiment.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_prospective_evidence_is_action_blind_but_causally_addressed() -> None:
    source = {
        "plan_id": "cp:one",
        "basis_revision": 12,
        "action_id": 3,
        "judgments": [{"prediction_id": "pp:one", "status": "supports"}],
    }
    projected = MODULE.epistemic_prospective_evidence(
        source, intervention_ref="im:opaque"
    )
    assert projected == {
        "plan_id": "cp:one",
        "basis_revision": 12,
        "judgments": [{"prediction_id": "pp:one", "status": "supports"}],
        "intervention_ref": "im:opaque",
    }
    assert not MODULE.BASE.QC._forbidden_input(projected)
    assert source["action_id"] == 3

