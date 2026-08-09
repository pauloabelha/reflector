from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v17_normalization_tested", HERE / "experiment.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_binding_keeps_exact_candidate_facts_without_witness_copy() -> None:
    value = {
        "schema_object_id": "schema:one",
        "template_hash": "template:one",
        "status": "ambiguous-active",
        "candidate_id": "candidate:one",
        "effect_pair": ["f00", "f01"],
        "population_complete": True,
        "effect_pair_count": 3,
        "grounding_count": 6,
        "legal_count": 7,
        "candidate_substitutions": [{"large": "duplicate"}],
        "effect_pairs": [{"large": "duplicate"}],
        "target_alpha_signature": "already-on-criticism",
    }
    normalized = MODULE.normalized_grounding_payload(value)
    assert normalized["candidate_id"] == "candidate:one"
    assert normalized["effect_pair"] == ["f00", "f01"]
    assert normalized["effect_pair_count"] == 3
    assert "candidate_substitutions" not in normalized
    assert "effect_pairs" not in normalized

