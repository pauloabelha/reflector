"""Model-in-the-loop information controls without environment actions."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Mapping

import causal_protocol as cp
import matched_executor
import snapshot_view


ACTION_KEYS = {"action_id", "fallback_action_id", "selected_action_id"}


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rehash(snapshot: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    value = json.loads(cp.stable_json(snapshot))
    value.pop("snapshot_hash", None)
    value["fixture_label"] = label
    value["snapshot_hash"] = cp.stable_hash(value)
    return value


def _permute(value: Any, mapping: Mapping[int, int], *, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            key: _permute(item, mapping, parent_key=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_permute(item, mapping, parent_key=parent_key) for item in value]
    if parent_key in ACTION_KEYS and isinstance(value, int):
        return int(mapping.get(int(value), int(value)))
    if parent_key in {"token", "action_token"} and isinstance(value, str):
        if value.startswith("A") and value[1:].isdigit():
            action = int(value[1:])
            return f"A{mapping.get(action, action)}"
    return value


def permuted_fixture(snapshot: Mapping[str, Any], mapping: Mapping[int, int]) -> dict[str, Any]:
    return _rehash(_permute(snapshot, mapping), label="coherent-action-effect-permutation")


def dependency_deleted_fixture(
    snapshot: Mapping[str, Any], *, transition_ids: set[str],
) -> dict[str, Any]:
    value = json.loads(cp.stable_json(snapshot))
    value["full_relevant_transition_history"] = [
        item for item in value["full_relevant_transition_history"]
        if str(item["transition_id"]) not in transition_ids
    ]
    value["dependency_deletion"] = {
        "removed_transition_ids": sorted(transition_ids),
        "purpose": "information-sensitivity-control-not-gameplay",
    }
    return _rehash(value, label="dependency-deletion")


def _selected(result: matched_executor.MatchedExecutorResult) -> int | None:
    if result.proposal is None:
        return None
    legal = [int(item["action_id"]) for item in result.proposal["candidate_actions"]]
    return cp.validate_decision_coherence(result.proposal, legal_actions=legal)


def _selected_candidate(result: matched_executor.MatchedExecutorResult) -> Mapping[str, Any] | None:
    selected = _selected(result)
    if selected is None or result.proposal is None:
        return None
    return next(
        item for item in result.proposal["candidate_actions"]
        if int(item["action_id"]) == selected
    )


def run(
    *, fifo: Any, sandbox: Any, model_config: Mapping[str, Any],
    python_config: Mapping[str, Any], full_snapshot: Mapping[str, Any],
    artifact_root: Path,
) -> dict[str, Any]:
    """Run paired B/C dependency and coherent-label sensitivity controls."""

    mapping = {1: 2, 2: 1, 3: 4, 4: 3, 5: 7, 7: 5}
    removed = {f"t{i:03d}" for i in range(8)}
    fixtures = {
        "original": _rehash(full_snapshot, label="control-original"),
        "permuted": permuted_fixture(full_snapshot, mapping),
        "dependency-deleted": dependency_deleted_fixture(
            full_snapshot, transition_ids=removed,
        ),
    }
    results: dict[str, dict[str, matched_executor.MatchedExecutorResult]] = {}
    failures: dict[str, str] = {}
    for fixture_name, snapshot in fixtures.items():
        results[fixture_name] = {}
        model_snapshot = snapshot_view.compact_model_view(snapshot)
        _write_json(artifact_root / fixture_name / "model-snapshot.json", model_snapshot)
        for arm in ("arm-b", "arm-c"):
            writer = lambda name, value, fixture_name=fixture_name, arm=arm: _write_json(
                artifact_root / fixture_name / arm / name, value
            )
            worker = matched_executor.MatchedExecutor(
                fifo=fifo, sandbox=sandbox, model_config=model_config,
                python_config=python_config, artifact_writer=writer,
            )
            try:
                result = worker.deliberate(
                    arm=arm, full_snapshot=snapshot, model_snapshot=model_snapshot,
                )
                results[fixture_name][arm] = result
                _write_json(artifact_root / fixture_name / arm / "result.json", asdict(result))
            except Exception as error:
                key = f"{fixture_name}:{arm}"
                failures[key] = f"{type(error).__name__}: {error}"
                _write_json(
                    artifact_root / fixture_name / arm / "failure.json",
                    {"error": failures[key]},
                )

    outcomes: dict[str, Any] = {}
    for arm in ("arm-b", "arm-c"):
        original = results.get("original", {}).get(arm)
        permuted = results.get("permuted", {}).get(arm)
        deleted = results.get("dependency-deleted", {}).get(arm)
        original_action = None if original is None else _selected(original)
        permuted_action = None if permuted is None else _selected(permuted)
        deleted_action = None if deleted is None else _selected(deleted)
        original_candidate = None if original is None else _selected_candidate(original)
        deleted_candidate = None if deleted is None else _selected_candidate(deleted)
        deleted_dependencies = set() if deleted_candidate is None else {
            str(item) for item in deleted_candidate["dependencies"]
        }
        dependency_sensitive = (
            original is not None and deleted is not None
            and (
                original_action != deleted_action
                or original_candidate != deleted_candidate
            )
            and not (deleted_dependencies & removed)
        )
        outcomes[arm] = {
            "original_action": original_action,
            "permuted_action": permuted_action,
            "expected_permuted_action": (
                None if original_action is None else mapping.get(original_action, original_action)
            ),
            "permutation_equivariant": (
                original_action is not None
                and permuted_action == mapping.get(original_action, original_action)
            ),
            "dependency_deleted_action": deleted_action,
            "dependency_sensitive": dependency_sensitive,
            "deleted_ids_not_recited": not bool(deleted_dependencies & removed),
            "treatments_engaged": {
                name: result.treatment.engaged
                for name, rows in results.items()
                if (result := rows.get(arm)) is not None
            },
            "resources": {
                name: {
                    "qwen_calls": result.qwen_calls,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "qwen_latency_s": result.qwen_latency_s,
                    "python_calls": result.python_calls,
                    "python_runtime_s": result.python_runtime_s,
                }
                for name, rows in results.items()
                if (result := rows.get(arm)) is not None
            },
        }
    summary = {
        "control": "model-in-the-loop-information-sensitivity",
        "mapping": {str(key): value for key, value in mapping.items()},
        "removed_transition_ids": sorted(removed),
        "environment_actions": 0,
        "failures": failures,
        "outcomes": outcomes,
        "passed": (
            not failures
            and all(
                row["permutation_equivariant"]
                and row["dependency_sensitive"]
                and row["deleted_ids_not_recited"]
                and all(row["treatments_engaged"].values())
                for row in outcomes.values()
            )
        ),
    }
    _write_json(artifact_root / "SUMMARY.json", summary)
    return summary
