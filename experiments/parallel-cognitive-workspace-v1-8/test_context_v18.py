from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _load():
    path = HERE / "experiment.py"
    spec = importlib.util.spec_from_file_location("test_prospective_workspace_v18", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_only_context_capacity_changes_from_v17() -> None:
    module = _load()
    current = module.load_config()
    prior = module.V17_MODULE.load_config()
    assert current["qwen"]["context_window_tokens"] == 24_576
    assert prior["qwen"]["context_window_tokens"] == 16_384
    normalized = {**current, "experiment": prior["experiment"], "protocol": prior["protocol"], "workspace_protocol": prior["workspace_protocol"], "qwen": {**current["qwen"], "context_window_tokens": 16_384}}
    assert normalized == prior


def test_v17_measured_requests_fit_with_frozen_reserve() -> None:
    module = _load()
    config = module.load_config()
    reserve = config["qwen"]["max_tokens"]
    window = config["qwen"]["context_window_tokens"]
    assert reserve == 2_048
    assert all(prompt + reserve <= window for prompt in (16_107, 20_499, 19_412))

