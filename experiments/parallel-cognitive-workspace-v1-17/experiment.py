"""One-game mechanism-transplant test over frozen v1.16 cognition."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V116 = HERE.parent / "parallel-cognitive-workspace-v1-16"
FROZEN_PARENT_COMMIT = "77bc32cdb489b43c6cfa4787cc4cff8d95b30d61"
ELIGIBLE_GAME_IDS = ("g50t", "ls20", "tr87", "wa30")
SELECTED_GAME = "wa30"
SELECTED_SCORE = "6b6a120480452cdcf70bfc74a113ff38f44f003f591816b9e4e8b1e1bf8bb6bf"


def _load(name: str, path: Path) -> Any:
    resolved = path.resolve()
    for existing in reversed(tuple(sys.modules.values())):
        existing_file = getattr(existing, "__file__", None)
        if existing_file is not None and Path(existing_file).resolve() == resolved:
            return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V116_MODULE = _load("prospective_workspace_v117_base", V116 / "experiment.py")
BASE = V116_MODULE.BASE


def selector_scores(game_ids: Sequence[str]) -> tuple[tuple[str, str], ...]:
    supplied = {str(game_id) for game_id in game_ids}
    candidates = [game_id for game_id in ELIGIBLE_GAME_IDS if game_id in supplied]
    return tuple(
        sorted(
            (
                hashlib.sha256(
                    f"{FROZEN_PARENT_COMMIT}|{game_id}".encode("utf-8")
                ).hexdigest(),
                game_id,
            )
            for game_id in candidates
        )
    )


def select_game(game_ids: Sequence[str]) -> tuple[str, str]:
    scores = selector_scores(game_ids)
    if not scores:
        raise ValueError("no non-ar25 candidate games")
    score, game = scores[0]
    return game, score


def validate_cli(argv: Sequence[str]) -> None:
    values = tuple(str(value) for value in argv)
    for index, value in enumerate(values):
        if value == "--games" or value.startswith("--games="):
            raise ValueError("v1.17 game selection is frozen; --games is forbidden")
        if value == "--profiles" or value.startswith("--profiles="):
            raise ValueError("v1.17 profile selection is frozen; --profiles is forbidden")
        if value == "--workers":
            if index + 1 >= len(values) or values[index + 1] != "2":
                raise ValueError("v1.17 requires exactly two environment workers")
        if value.startswith("--workers=") and value != "--workers=2":
            raise ValueError("v1.17 requires exactly two environment workers")


def load_config() -> dict[str, Any]:
    config = V116_MODULE.load_config()
    config.update(json.loads((HERE / "config.json").read_text(encoding="utf-8")))
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V116_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        **{
            f"v1.17/{name}": BASE.LEDGER.file_hash(HERE / name)
            for name in ("experiment.py", "config.json", "PROPOSAL.md", "SELECTION.json")
        },
    }
    body["transplant_selector"] = dict(config["transplant_selector"])
    body["changes_from_v1.16"] = [
        "deterministically selected non-ar25 game identity",
        "mechanism-transplant verdict with level completion reported as a bonus",
    ]
    return {**body, "manifest_digest": BASE.LEDGER.stable_hash(body)}


def job_key(
    game: str,
    arm: str,
    profile_id: str,
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> str:
    return BASE.LEDGER.stable_hash(
        {
            "protocol": config["workspace_protocol"],
            "game": game,
            "arm": arm,
            "profile": profile_id,
            "config": config,
            "manifest_digest": manifest["manifest_digest"],
        }
    )


def evaluate_transplant_gate(
    results: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    del config
    by_arm = {str(item["arm_id"]): item for item in results}
    if set(by_arm) != {"r2_only", "shared_live_qwen"}:
        return {"verdict": "INVALID", "reasons": ["paired-arm-result-missing"]}
    control = by_arm["r2_only"]
    shared = by_arm["shared_live_qwen"]
    validity = {
        "same_initial_digest": control.get("initial_digest") == shared.get("initial_digest"),
        "factual_replay": bool(control.get("replay_verified"))
        and bool(shared.get("replay_verified")),
        "counterfactual_replay": bool(shared.get("counterfactual_exact")),
        "context": bool(shared.get("qwen_context_valid")),
        "transport": bool(shared.get("qwen_transport_successful"))
        and int(shared.get("qwen_valid_compilations", 0))
        == int(shared.get("qwen_calls", 0)),
        "support_authority": int(control.get("support_authority_violations", 0)) == 0
        and int(shared.get("support_authority_violations", 0)) == 0,
    }
    invalid = [name for name, value in validity.items() if not value]
    if invalid:
        return {"verdict": "INVALID", "validity": validity, "reasons": invalid}
    chain = dict(shared.get("prospective_chain", {}))
    groundings = list(shared.get("groundings", []))
    gates = {
        "initial_ambiguous_qwen_grounding": any(
            int(item.get("effect_pair_count", 0)) > 1 for item in groundings
        ),
        "prospective_evidence": int(chain.get("supported_predictions", 0)) > 0,
        "evidence_driven_non_alpha_revision": int(
            chain.get("evidence_citing_revision_derivations", 0)
        )
        > 0,
        "unique_confirmed_revision_binding": int(
            chain.get("confirmed_revision_bindings", 0)
        )
        > 0,
        "revised_control_changed_action": int(
            chain.get("changed_control_decisions", 0)
        )
        > 0,
        "same_state_branch_favorable": int(
            shared.get("counterfactual_favorable_count", 0)
        )
        > 0,
    }
    failed = [name for name, value in gates.items() if not value]
    if failed:
        verdict = "FAIL"
    elif bool(shared.get("first_level_completed")) and (
        not bool(control.get("first_level_completed"))
        or int(shared.get("actions", 0)) < int(control.get("actions", 0))
    ):
        verdict = "SCORE_PASS"
    else:
        verdict = "PASS"
    return {"verdict": verdict, "validity": validity, "gates": gates, "reasons": failed}


BASE.HERE = HERE
BASE.ARTIFACTS = HERE / "artifacts"
BASE.load_config = load_config
BASE.build_manifest = build_manifest
BASE._job_key = job_key
BASE.evaluate_binary_gate = evaluate_transplant_gate


def main(argv: Sequence[str] | None = None) -> int:
    effective = tuple(sys.argv[1:] if argv is None else argv)
    validate_cli(effective)
    return int(BASE.main(effective))


if __name__ == "__main__":
    raise SystemExit(main())
