from __future__ import annotations

from reflector2.workspace_main import (
    PROVEN_EXPERIMENT,
    PROVEN_PROTOCOL,
    load_proven_experiment,
    verified_result_available,
)


def test_primary_workspace_loads_exact_proven_protocol() -> None:
    assert PROVEN_EXPERIMENT.is_file()
    module = load_proven_experiment()
    config = module.load_config()
    assert config["workspace_protocol"] == PROVEN_PROTOCOL
    assert config["arms"] == ["r2_only", "shared_live_qwen"]


def test_primary_workspace_has_fresh_pass_evidence_record() -> None:
    assert verified_result_available()
