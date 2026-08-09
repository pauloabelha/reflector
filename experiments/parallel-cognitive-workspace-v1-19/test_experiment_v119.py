from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_module():
    path = HERE / "experiment.py"
    spec = importlib.util.spec_from_file_location("test_workspace_v119", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_capacity_is_the_only_runtime_overlay():
    module = load_module()
    current = module.load_config()
    prior = module.V118_MODULE.load_config()
    assert current["profiles"]["generic_prospective"]["frontier_token_budget"] == 10000
    normalized = dict(current)
    normalized.update(
        experiment=prior["experiment"],
        protocol=prior["protocol"],
        workspace_protocol=prior["workspace_protocol"],
    )
    normalized["profiles"] = {
        **normalized["profiles"],
        "generic_prospective": prior["profiles"]["generic_prospective"],
    }
    assert normalized == prior


def test_preserved_failure_frontier_fits_exactly_without_optional_fill():
    module = load_module()
    root = (
        module.V118
        / "artifacts/workspaces/generic_prospective--wa30--shared_live_qwen"
    )
    if not root.exists():
        return
    state, _events = module.BASE.rebuild_graph(root)
    orientation_objects = [
        item for item in state.objects if item.kind == "qwen_orientation"
    ]
    orientation = max(
        orientation_objects, key=lambda item: (item.created_revision, item.object_id)
    ).payload
    cut = module.BASE.QC.sparse_cut(
        state,
        token_budget=10000,
        focus_ids=tuple(orientation["focus_ids"]),
        expansion_ids=tuple(orientation["expansion_ids"]),
    )
    kinds = [item["kind"] for item in cut["objects"]]
    assert cut["dependency_closed"] is True
    assert cut["used_tokens"] <= 10000
    assert len(cut["objects"]) == 28
    assert kinds.count("binding") == 9
    assert kinds.count("structured_criticism") == 1
    assert kinds.count("qwen_derivation") == 1
