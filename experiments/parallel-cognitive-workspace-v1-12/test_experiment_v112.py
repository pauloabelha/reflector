from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXPERIMENT = load("workspace_v112_experiment_test", HERE / "experiment.py")


def test_v112_config_and_adapters_are_frozen() -> None:
    config = EXPERIMENT.load_config()
    assert config["action_budget"] == 64
    assert config["qwen"]["trigger_action_counts"] == [0, 8, 16, 24]
    assert config["qwen"]["max_tokens"] == 3072
    assert config["qwen"]["reserved_tokens"] == 3072
    assert EXPERIMENT.BASE.QC._CAUSAL_PACKET_V112_INSTALLED is True
    assert hasattr(EXPERIMENT.BASE.QC, "_revision_response_base_schema")


def test_action_free_grounding_carries_temporal_facts_and_no_action_token() -> None:
    before = tuple(tuple(0 for _ in range(5)) for _ in range(5))
    after = before
    raw, _ = EXPERIMENT.BASE.V0.relational_state(after, 2, ())
    temporal = EXPERIMENT.BASE.V0.motion_relations(before, after)
    assert all("action" not in str(item).lower() for item in temporal)
    assert "opaque_legal_action_count" in raw  # stripped only at packet boundary
