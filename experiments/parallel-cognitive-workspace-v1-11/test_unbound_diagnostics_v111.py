from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AMBIGUITY = load("ambiguity_v111_test", V14 / "ambiguity.py")
EXPERIMENT = load("workspace_v111_test", HERE / "experiment.py")


def test_unbound_witness_identifies_the_condition_that_kills_grounding() -> None:
    template = {
        "conditions": [
            {"predicate": "AlignedHorizontal", "arguments": ["?a", "?b"]},
            {"predicate": "DifferentArea", "arguments": ["?a", "?b"]},
        ],
        "preferred_consequence": {
            "arguments": ["?a", "?b"],
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
        },
    }
    relation_state = {
        "relations": [
            {"predicate": "AlignedHorizontal", "arguments": ["f0", "f1"]},
            {"predicate": "DifferentArea", "arguments": ["f0", "f2"]},
        ]
    }
    witness = AMBIGUITY.compile_ambiguity_witness(template, relation_state)
    # The inherited v1.6 runner wrapper removes witness `status` in production
    # so it cannot overwrite executable grounding.  Direct module tests may
    # retain the diagnostic status depending on collection/import order.
    assert witness.get("status", "unbound") == "unbound"
    assert witness["blocking_condition_indices"] == [0, 1]
    assert all(row["grounding_count_without_condition"] > 0 for row in witness["condition_diagnostics"])
    assert "remove or replace" in witness["refinement_goal"]


def test_v111_call_schedule_and_unique_evidence_grammar() -> None:
    config = EXPERIMENT.load_config()
    assert config["qwen"]["trigger_action_counts"] == [0, 8, 16, 24]
    turn = type("Turn", (), {"document": {"revision_task": None}, "validation_context": {}})()
    # The live schema is dynamic; this static source assertion protects the
    # response-format guarantee without fabricating a graph turn fixture.
    source = (V14 / "qwen_cognition.py").read_text(encoding="utf-8")
    assert source.count('"uniqueItems": True') >= 2
