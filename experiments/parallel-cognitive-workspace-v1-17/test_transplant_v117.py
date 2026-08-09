from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("prospective_workspace_v117_tested", HERE / "experiment.py")
assert SPEC is not None and SPEC.loader is not None
EXP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXP
SPEC.loader.exec_module(EXP)


GAME_IDS = (
    "ar25", "bp35", "cd82", "cn04", "dc22", "ft09", "g50t", "ka59",
    "lf52", "lp85", "ls20", "m0r0", "r11l", "re86", "s5i5", "sb26",
    "sc25", "sk48", "sp80", "su15", "tn36", "tr87", "tu93", "vc33", "wa30",
)


def _result(arm: str) -> dict:
    return {
        "arm_id": arm,
        "initial_digest": "same",
        "replay_verified": True,
        "counterfactual_exact": True,
        "qwen_context_valid": True,
        "qwen_transport_successful": True,
        "qwen_valid_compilations": 0 if arm == "r2_only" else 3,
        "qwen_calls": 0 if arm == "r2_only" else 3,
        "support_authority_violations": 0,
        "actions": 64,
        "first_level_completed": False,
        "counterfactual_favorable_count": 0,
        "groundings": [],
        "prospective_chain": {},
    }


def test_frozen_selector_chooses_wa30_from_metadata_eligible_population() -> None:
    game, score = EXP.select_game(GAME_IDS)
    assert game == EXP.SELECTED_GAME == "wa30"
    assert score == EXP.SELECTED_SCORE
    assert {game_id for _, game_id in EXP.selector_scores(GAME_IDS)} == set(EXP.ELIGIBLE_GAME_IDS)
    config = EXP.load_config()
    assert config["games"] == [game]


def test_transplant_pass_requires_full_chain_but_not_level_completion() -> None:
    control = _result("r2_only")
    shared = _result("shared_live_qwen")
    shared.update(
        {
            "groundings": [{"effect_pair_count": 3}, {"effect_pair_count": 1}],
            "counterfactual_favorable_count": 1,
            "prospective_chain": {
                "supported_predictions": 2,
                "evidence_citing_revision_derivations": 1,
                "confirmed_revision_bindings": 1,
                "changed_control_decisions": 1,
            },
        }
    )
    verdict = EXP.evaluate_transplant_gate([control, shared], {})
    assert verdict["verdict"] == "PASS"
    assert all(verdict["gates"].values())


def test_transplant_gate_rejects_missing_link_and_invalid_replay() -> None:
    control = _result("r2_only")
    shared = _result("shared_live_qwen")
    assert EXP.evaluate_transplant_gate([control, shared], {})["verdict"] == "FAIL"
    shared["replay_verified"] = False
    assert EXP.evaluate_transplant_gate([control, shared], {})["verdict"] == "INVALID"


def test_config_is_only_runtime_game_change_over_v116() -> None:
    inherited = EXP.V116_MODULE.load_config()
    current = EXP.load_config()
    allowed = {"experiment", "protocol", "workspace_protocol", "games", "transplant_selector", "binary_gate"}
    differing = {key for key in set(inherited) | set(current) if inherited.get(key) != current.get(key)}
    assert differing <= allowed
    for key in set(inherited) - allowed:
        assert current[key] == inherited[key]
    json.dumps(current, sort_keys=True)


def test_cli_cannot_override_frozen_job_shape() -> None:
    EXP.validate_cli(("--dry-run", "--workers", "2"))
    for argv in (("--games", "g50t"), ("--profiles", "other"), ("--workers", "1")):
        try:
            EXP.validate_cli(argv)
        except ValueError:
            pass
        else:
            raise AssertionError(f"override unexpectedly accepted: {argv}")
