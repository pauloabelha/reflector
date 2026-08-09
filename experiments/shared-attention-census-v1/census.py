"""Whole-public-suite paired census selection, manifest, and analysis.

The module is deliberately separate from the ARC runner and graph.  It freezes
eligible transports, describes paired jobs, extracts causal pickup/cost
evidence from completed workspace ledgers, and classifies paired outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_RECORDINGS = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/recordings/reflector-v14-graph-400"
)
DEFAULT_ENVIRONMENTS = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/environment_files"
)
WORKSPACE_MODULE = HERE.parent / "parallel-cognitive-workspace-v0" / "workspace.py"

PROTOCOL = "shared-attention-census-v1.0"
EXPECTED_GAME_IDS = (
    "ar25",
    "bp35",
    "cd82",
    "cn04",
    "dc22",
    "ft09",
    "g50t",
    "ka59",
    "lf52",
    "lp85",
    "ls20",
    "m0r0",
    "r11l",
    "re86",
    "s5i5",
    "sb26",
    "sc25",
    "sk48",
    "sp80",
    "su15",
    "tn36",
    "tr87",
    "tu93",
    "vc33",
    "wa30",
)
ARMS = (
    {
        "arm_id": "r2_only",
        "harness_arm": "workspace_no_qwen",
        "qwen_enabled": False,
    },
    {
        "arm_id": "shared_attention_qwen",
        "harness_arm": "parallel_qwen",
        "qwen_enabled": True,
    },
)
ARCHITECTURE_PROFILES = (
    {
        "profile_id": "balanced",
        "action_budget": 32,
        "frontier_root_limit": 12,
        "frontier_token_budget": 2400,
        "proposal_attention_boost": 1.0,
        "attention_half_life_actions": 12,
        "trigger_action_counts": [0, 8, 16],
        "max_calls_per_episode": 3,
        "qwen_max_tokens": 900,
        "qwen_thinking_budget_tokens": 256,
    },
    {
        "profile_id": "wide_frontier",
        "action_budget": 32,
        "frontier_root_limit": 24,
        "frontier_token_budget": 3200,
        "proposal_attention_boost": 1.0,
        "attention_half_life_actions": 12,
        "trigger_action_counts": [0, 8, 16],
        "max_calls_per_episode": 3,
        "qwen_max_tokens": 900,
        "qwen_thinking_budget_tokens": 256,
    },
    {
        "profile_id": "persistent_proposal",
        "action_budget": 32,
        "frontier_root_limit": 12,
        "frontier_token_budget": 2400,
        "proposal_attention_boost": 2.0,
        "attention_half_life_actions": 24,
        "trigger_action_counts": [0, 8, 16],
        "max_calls_per_episode": 3,
        "qwen_max_tokens": 900,
        "qwen_thinking_budget_tokens": 256,
    },
)

# Backward-compatible import name for draft census consumers.  These are
# architecture profiles, not Qwen cadence settings.
ARCHITECTURE_SETTINGS = ARCHITECTURE_PROFILES

# Measured on the completed ar25 v0 arms.  These are planning constants, never
# evidence in the outcome analysis.
REFERENCE_R2_SECONDS = 41.08148110500042
REFERENCE_SHARED_4_CALL_SECONDS = 261.5945360620026
REFERENCE_QWEN_INCREMENT_SECONDS = (
    REFERENCE_SHARED_4_CALL_SECONDS - REFERENCE_R2_SECONDS
) / 4


class CensusError(RuntimeError):
    """Raised when corpus or paired-result invariants do not hold."""


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_recordings(root: Path) -> dict[str, Path]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(root.glob("*.recording.jsonl")):
        grouped[path.name.split(".", 1)[0]].append(path)
    duplicates = {game: paths for game, paths in grouped.items() if len(paths) != 1}
    if duplicates:
        raise CensusError(
            "recording multiplicity: "
            + ", ".join(f"{game}={len(paths)}" for game, paths in sorted(duplicates.items()))
        )
    return {game: paths[0] for game, paths in sorted(grouped.items())}


def discover_environments(root: Path) -> dict[str, dict[str, Path]]:
    found: dict[str, dict[str, Path]] = {}
    for game_dir in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda item: item.name):
        revisions = sorted(item for item in game_dir.iterdir() if item.is_dir())
        valid = [
            revision
            for revision in revisions
            if (revision / f"{game_dir.name}.py").is_file()
            and (revision / "metadata.json").is_file()
        ]
        if len(valid) != 1:
            continue
        revision = valid[0]
        found[game_dir.name] = {
            "revision_dir": revision,
            "implementation": revision / f"{game_dir.name}.py",
            "metadata": revision / "metadata.json",
        }
    return found


def select_corpus(recordings_root: Path, environments_root: Path) -> dict[str, Any]:
    recordings = discover_recordings(recordings_root)
    environments = discover_environments(environments_root)
    games = sorted(set(recordings) & set(environments))
    rows = []
    for game in games:
        environment = environments[game]
        rows.append(
            {
                "game": game,
                "recording": str(recordings[game]),
                "recording_sha256": file_hash(recordings[game]),
                "environment_revision": environment["revision_dir"].name,
                "environment_implementation": str(environment["implementation"]),
                "environment_implementation_sha256": file_hash(environment["implementation"]),
                "environment_metadata": str(environment["metadata"]),
                "environment_metadata_sha256": file_hash(environment["metadata"]),
            }
        )
    return {
        "selection_rule": (
            "lexicographic intersection of unique public recording prefixes and game directories "
            "having exactly one revision with <game>.py plus metadata.json"
        ),
        "recording_only": sorted(set(recordings) - set(environments)),
        "environment_only": sorted(set(environments) - set(recordings)),
        "games": rows,
        "game_ids": games,
        "corpus_digest": stable_hash(rows),
    }


def estimate_runtime(game_count: int, profiles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    qwen_calls = game_count * sum(int(item["max_calls_per_episode"]) for item in profiles)
    maximum_actions = game_count * len(profiles) * len(ARMS) * 32
    shared_seconds = sum(
        game_count
        * (REFERENCE_R2_SECONDS + REFERENCE_QWEN_INCREMENT_SECONDS * int(item["max_calls_per_episode"]))
        for item in profiles
    )
    # R2 controls can occupy four independent workers while the resident Qwen
    # server serializes the shared arms.
    control_seconds_four_workers = game_count * len(profiles) * REFERENCE_R2_SECONDS / 4
    central_seconds = shared_seconds + control_seconds_four_workers
    planned_seconds = central_seconds * 1.15
    return {
        "method": "measured ar25 v0 arm elapsed time; one resident Qwen stream; four R2-only workers; 15% census overhead",
        "reference_r2_seconds": REFERENCE_R2_SECONDS,
        "reference_shared_four_call_seconds": REFERENCE_SHARED_4_CALL_SECONDS,
        "derived_incremental_seconds_per_qwen_call": REFERENCE_QWEN_INCREMENT_SECONDS,
        "maximum_environment_actions": maximum_actions,
        "maximum_qwen_calls": qwen_calls,
        "paired_episode_count": game_count * len(profiles) * len(ARMS),
        "central_estimate_seconds": central_seconds,
        "planned_estimate_seconds": planned_seconds,
        "planned_estimate_hours": planned_seconds / 3600,
        "serial_gpu_hours": qwen_calls * REFERENCE_QWEN_INCREMENT_SECONDS / 3600,
        "operational_range_hours": [5.0, 7.0],
    }


def build_manifest(
    recordings_root: Path = DEFAULT_RECORDINGS,
    environments_root: Path = DEFAULT_ENVIRONMENTS,
) -> dict[str, Any]:
    corpus = select_corpus(recordings_root, environments_root)
    if tuple(corpus["game_ids"]) != EXPECTED_GAME_IDS:
        raise CensusError(
            f"public corpus changed: expected {list(EXPECTED_GAME_IDS)}, observed {corpus['game_ids']}"
        )
    jobs = []
    for profile in ARCHITECTURE_PROFILES:
        for game in corpus["game_ids"]:
            pair_id = f"{profile['profile_id']}--{game}"
            for arm in ARMS:
                jobs.append(
                    {
                        "job_id": f"{pair_id}--{arm['arm_id']}",
                        "pair_id": pair_id,
                        "profile_id": profile["profile_id"],
                        "game": game,
                        "arm_id": arm["arm_id"],
                        "harness_arm": arm["harness_arm"],
                        "fresh_start_required": True,
                        "resume_from_prior_experiment_forbidden": True,
                    }
                )
    manifest = {
        "protocol": PROTOCOL,
        "selection": corpus,
        "paired_design": {
            "arms": list(ARMS),
            "profiles": list(ARCHITECTURE_PROFILES),
            "primary_profile": "balanced",
            "profile_sweep_axis": "global salience/frontier architecture",
            "same_environment_revision_within_pair": True,
            "same_initial_observation_digest_required": True,
            "fresh_workspace_per_job": True,
            "action_budget_identical_within_pair": True,
            "pair_order_not_used_in_analysis": True,
        },
        "jobs": jobs,
        "runtime_estimate": estimate_runtime(len(corpus["game_ids"]), ARCHITECTURE_PROFILES),
    }
    return {**manifest, "manifest_digest": stable_hash(manifest)}


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)


def pickup_chain_metrics_from_records(
    tasks: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
    replies: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Measure explicit R->Q, Q->R, and bidirectional pickup chains."""

    task_by_id = {str(item["task_id"]): item for item in tasks}
    post_initial_tasks = {
        task_id
        for task_id, item in task_by_id.items()
        if int(item.get("basis_version", item.get("basis_observation_version", 0))) > 0
        and bool(item.get("recent_transition_count", item.get("has_recent_transitions", True)))
    }
    template_source: dict[str, str] = {}
    bound_tasks: set[str] = set()
    for item in adjudications:
        task_id = str(item.get("task_id", ""))
        if task_id not in task_by_id:
            continue
        groundings = list(item.get("groundings", ()))
        bound_statuses = {"bound", "duplicate-active", "active-zero-evidence"}
        if any(str(value.get("status", "")) in bound_statuses for value in groundings):
            bound_tasks.add(task_id)
        for template, grounding in zip(item.get("accepted_templates", ()), groundings, strict=False):
            if str(grounding.get("status", "")) not in bound_statuses:
                continue
            digest = template.get("canonical_hash", template.get("template_hash"))
            if digest:
                # Ledger order makes the first successful activation the causal
                # source; later duplicate proposals cannot claim its decisions.
                template_source.setdefault(str(digest), task_id)
    q_to_r_tasks: set[str] = set()
    q_to_r_decisions = 0
    q_to_r_changed_decisions = 0
    for item in decisions:
        decision = item.get("decision", item)
        if not bool(decision.get("prior_used")):
            continue
        digest = str(decision.get("template_hash", ""))
        source = template_source.get(digest)
        if source is None:
            continue
        q_to_r_tasks.add(source)
        q_to_r_decisions += 1
        if bool(item.get("qwen_changed_action", item.get("changed_from_no_qwen", False))):
            q_to_r_changed_decisions += 1
    token_usage = Counter()
    reply_latency = 0.0
    for item in replies:
        reply_latency += float(item.get("latency_s", 0.0) or 0.0)
        usage = item.get("usage", {})
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            token_usage[key] += int(usage.get(key, 0) or 0)
    bidirectional = post_initial_tasks & q_to_r_tasks
    return {
        "available": True,
        "task_count": len(task_by_id),
        "r_to_q_pickup_tasks": len(post_initial_tasks),
        "q_to_r_bound_tasks": len(bound_tasks),
        "q_to_r_pickup_tasks": len(q_to_r_tasks),
        "q_to_r_prior_decisions": q_to_r_decisions,
        "q_to_r_changed_decisions": q_to_r_changed_decisions,
        "bidirectional_pickup_tasks": len(bidirectional),
        "bidirectional_task_ids": sorted(bidirectional),
        "qwen_reply_latency_s": reply_latency,
        "qwen_prompt_tokens": token_usage["prompt_tokens"],
        "qwen_completion_tokens": token_usage["completion_tokens"],
        "qwen_total_tokens": token_usage["total_tokens"],
    }


def _workspace_api() -> Any:
    spec = importlib.util.spec_from_file_location("shared_attention_census_workspace", WORKSPACE_MODULE)
    if spec is None or spec.loader is None:
        raise CensusError(f"cannot load workspace API: {WORKSPACE_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def pickup_chain_metrics(workspace_root: Path) -> dict[str, Any]:
    """Extract exact pickup and Qwen cost evidence from one completed ledger."""

    workspace = _workspace_api()
    events = workspace.list_events(workspace_root)
    state = workspace.reduce_events(events)
    tasks = []
    for task in state.tasks:
        projection = workspace.read_blob(workspace_root, task.projection_blob)
        tasks.append(
            {
                "task_id": task.task_id,
                "basis_version": task.basis_version,
                "recent_transition_count": len(projection.get("recent_transitions", ())),
            }
        )
    adjudications = []
    decisions = []
    replies = []
    for event in events:
        if event["type"] == "ExternalProposalAdjudicated":
            adjudications.append(
                workspace.read_blob(workspace_root, str(event["payload"]["adjudication_blob"]))
            )
        elif event["type"] == "R2DecisionPublished":
            decisions.append(workspace.read_blob(workspace_root, str(event["payload"]["decision_blob"])))
        elif event["type"] == "QwenReplyRecorded":
            reply = workspace.read_blob(workspace_root, str(event["payload"]["response_blob"]))
            usage = {}
            raw_body = reply.get("raw_body")
            if isinstance(raw_body, str):
                try:
                    envelope = json.loads(raw_body)
                    usage = envelope.get("usage", {}) if isinstance(envelope, Mapping) else {}
                except json.JSONDecodeError:
                    usage = {}
            replies.append({"latency_s": reply.get("latency_s", 0.0), "usage": usage})
    return pickup_chain_metrics_from_records(tasks, adjudications, decisions, replies)


def enrich_arm_result(result: Mapping[str, Any], workspace_root: Path | None = None) -> dict[str, Any]:
    value = dict(result)
    if workspace_root is None:
        value.setdefault("pickup", {"available": False})
        return value
    workspace = _workspace_api()
    state = workspace.reduce_workspace(workspace_root)
    initial_digest = state.observations[0][1] if state.observations else None
    value["initial_observation_digest"] = initial_digest
    value["pickup"] = pickup_chain_metrics(workspace_root)
    return value


def _count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Mapping):
        for key in ("count", "total", "complete", "value"):
            if key in value:
                return _count(value[key])
        return len(value)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _metric_sources(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for key in ("epistemic_metrics", "graph_metrics", "telemetry", "metrics"):
        value = result.get(key)
        if isinstance(value, Mapping):
            sources.append(value)
    sources.append(result)
    return sources


def _first_metric(sources: Sequence[Mapping[str, Any]], aliases: Sequence[str]) -> Any:
    for source in sources:
        for key in aliases:
            if key in source:
                return source[key]
    return None


def _novelty_counts(sources: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    aliases = {
        "ahead_of_r2": "ahead_of_r2",
        "ahead-of-r2": "ahead_of_r2",
        "refinement": "refinement",
        "paraphrase": "paraphrase",
        "inert": "inert",
        "harmful": "harmful",
    }
    counts = {value: 0 for value in aliases.values()}
    raw = _first_metric(
        sources,
        ("qwen_novelty_counts", "novelty_counts", "qwen_novelty", "novelty_classifications"),
    )
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            normalized = aliases.get(str(key).lower().replace(" ", "_"))
            if normalized:
                counts[normalized] += _count(value)
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Mapping):
                label = item.get("classification", item.get("label", item.get("novelty")))
            else:
                label = item
            normalized = aliases.get(str(label).lower().replace(" ", "_"))
            if normalized:
                counts[normalized] += 1
    return counts


def normalized_episode_telemetry(result: Mapping[str, Any]) -> dict[str, Any]:
    """Prefer graph-native causal telemetry, retaining v0-ledger compatibility."""

    sources = _metric_sources(result)
    graph_keys = {
        "N_QR", "N_RQ", "n_qr", "n_rq", "pickup_directions",
        "complete_causal_chains", "novelty_counts", "qwen_novelty_counts",
    }
    graph_native = any(any(key in source for key in graph_keys) for source in sources)
    directions = _first_metric(sources, ("pickup_directions",))
    if not isinstance(directions, Mapping):
        directions = {}
    n_qr_raw = _first_metric(
        sources, ("N_QR", "n_qr", "qwen_to_r2_pickups", "qwen_to_r2_pickup_count")
    )
    n_rq_raw = _first_metric(
        sources, ("N_RQ", "n_rq", "r2_to_qwen_pickups", "r2_to_qwen_pickup_count")
    )
    n_qr = _count(n_qr_raw if n_qr_raw is not None else directions.get("qwen->r2"))
    n_rq = _count(n_rq_raw if n_rq_raw is not None else directions.get("r2->qwen"))
    pickup = result.get("pickup", {})
    if not isinstance(pickup, Mapping):
        pickup = {}
    if not graph_native:
        n_qr = _count(pickup.get("q_to_r_pickup_tasks"))
        n_rq = _count(pickup.get("r_to_q_pickup_tasks"))
    novelty = _novelty_counts(sources)
    complete_chains = _count(
        _first_metric(
            sources,
            ("complete_causal_chains", "complete_grounded_causal_chains", "causal_chains_complete"),
        )
    )
    support_violations = _count(
        _first_metric(
            sources,
            ("support_authority_violations", "support_policy_violations", "support_violations"),
        )
    )
    unsupported_influence = _count(
        _first_metric(sources, ("unsupported_action_influence", "unsupported_action_influences"))
    )
    crowd_out = _count(
        _first_metric(sources, ("supported_r2_crowd_out", "r2_frontier_crowd_out"))
    )
    context_raw = _first_metric(
        sources, ("qwen_context_valid", "context_valid", "frontier_context_valid")
    )
    transport_raw = _first_metric(
        sources, ("qwen_transport_successful", "transport_successful", "qwen_request_success")
    )
    return {
        "telemetry_source": "graph_native" if graph_native else "v0_fallback",
        "N_QR": n_qr,
        "N_RQ": n_rq,
        "complete_causal_chains": complete_chains,
        "novelty_counts": novelty,
        "meaningful_novelty": novelty["ahead_of_r2"] + novelty["refinement"],
        "support_authority_violations": support_violations,
        "unsupported_action_influence": unsupported_influence,
        "supported_r2_crowd_out": crowd_out,
        "qwen_context_valid": bool(context_raw) if context_raw is not None else False,
        "qwen_transport_successful": bool(transport_raw) if transport_raw is not None else False,
        "qwen_reply_latency_s": float(
            _first_metric(sources, ("qwen_reply_latency_s", "qwen_latency_s"))
            or pickup.get("qwen_reply_latency_s", 0.0)
            or 0.0
        ),
        "qwen_total_tokens": _count(
            _first_metric(sources, ("qwen_total_tokens", "total_qwen_tokens"))
            or pickup.get("qwen_total_tokens", 0)
        ),
        "qwen_calls": _count(
            _first_metric(sources, ("qwen_calls", "qwen_call_count", "qwen_task_count"))
            or result.get("qwen_task_count", pickup.get("task_count", 0))
        ),
    }


def _arm_id(value: Mapping[str, Any]) -> str:
    arm = str(value.get("arm_id", value.get("arm", "")))
    mapping = {
        "r2_only": "r2_only",
        "workspace_no_qwen": "r2_only",
        "shared_attention_qwen": "shared_attention_qwen",
        "parallel_qwen": "shared_attention_qwen",
    }
    if arm not in mapping:
        raise CensusError(f"unknown census arm: {arm}")
    return mapping[arm]


def _profile_id(value: Mapping[str, Any]) -> str:
    profile = value.get("profile_id", value.get("profile", value.get("setting_id")))
    if profile is None:
        raise CensusError("result has no profile_id")
    return str(profile)


def _manifest_profiles(manifest: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    design = manifest["paired_design"]
    profiles = design.get("profiles", design.get("settings"))
    if not isinstance(profiles, Sequence):
        raise CensusError("manifest has no architecture profiles")
    return profiles


def classify_pair(control: Mapping[str, Any], shared: Mapping[str, Any]) -> dict[str, Any]:
    same_start = (
        control.get("initial_observation_digest") is not None
        and control.get("initial_observation_digest") == shared.get("initial_observation_digest")
    )
    replay_valid = bool(control.get("replay_verified")) and bool(shared.get("replay_verified"))
    control_levels = int(control.get("levels_completed", 0))
    shared_levels = int(shared.get("levels_completed", 0))
    control_actions = int(control.get("actions", 0))
    shared_actions = int(shared.get("actions", 0))
    both_complete = bool(control.get("first_level_completed")) and bool(shared.get("first_level_completed"))
    savings = None
    if both_complete and control_actions > 0:
        savings = (control_actions - shared_actions) / control_actions
    completion_gain = shared_levels > control_levels
    action_gain = bool(savings is not None and savings >= 0.25)
    hard_level_regression = shared_levels < control_levels
    substantial_action_increase = bool(savings is not None and savings <= -0.25)
    telemetry = normalized_episode_telemetry(shared)
    n_qr = telemetry["N_QR"]
    n_rq = telemetry["N_RQ"]
    complete_chains = telemetry["complete_causal_chains"]
    harmful_reasons = []
    if hard_level_regression:
        harmful_reasons.append("hard-level-regression")
    if telemetry["unsupported_action_influence"]:
        harmful_reasons.append("unsupported-action-influence")
    if telemetry["supported_r2_crowd_out"]:
        harmful_reasons.append("supported-r2-crowd-out")
    if substantial_action_increase:
        harmful_reasons.append("substantial-action-increase")
    harmful = bool(harmful_reasons)
    invalid = not replay_valid or not same_start or bool(control.get("error")) or bool(shared.get("error"))
    task_gain = completion_gain or action_gain
    if invalid:
        bucket = "INVALID"
        label = "invalid-replay-or-start-pair"
    elif complete_chains > 0 and task_gain and not hard_level_regression:
        bucket = "A"
        label = "complete-causal-transfer-plus-task-gain"
    elif n_qr > 0 and n_rq > 0 and not task_gain:
        bucket = "B"
        label = "grounded-bidirectional-pickup-without-task-gain"
    elif telemetry["meaningful_novelty"] > 0 and n_qr == 0:
        bucket = "C"
        label = "non-paraphrastic-proposal-without-r2-pickup"
    else:
        bucket = "D"
        label = "no-meaningful-qwen-novelty"
    return {
        "bucket": bucket,
        "bucket_label": label,
        "same_initial_observation": same_start,
        "replay_valid": replay_valid,
        "completion_delta": shared_levels - control_levels,
        "action_savings_fraction": savings,
        "completion_gain": completion_gain,
        "action_gain": action_gain,
        "task_gain": task_gain,
        "unattributed_task_gain": task_gain and bucket != "A",
        "hard_level_regression": hard_level_regression,
        "substantial_action_increase": substantial_action_increase,
        "harmful": harmful,
        "harmful_reasons": harmful_reasons,
        **telemetry,
        # Old field names remain in reports for downstream notebooks.
        "r_to_q_pickup_tasks": n_rq,
        "q_to_r_pickup_tasks": n_qr,
        "bidirectional_pickup_tasks": min(n_qr, n_rq),
        "shared_elapsed_s": float(shared.get("elapsed_s", 0.0) or 0.0),
        "r2_elapsed_s": float(control.get("elapsed_s", 0.0) or 0.0),
        "elapsed_overhead_s": float(shared.get("elapsed_s", 0.0) or 0.0)
        - float(control.get("elapsed_s", 0.0) or 0.0),
    }


def analyze_results(
    results: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    *,
    require_complete: bool = True,
) -> dict[str, Any]:
    indexed: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for item in results:
        key = (_profile_id(item), str(item["game"]), _arm_id(item))
        if key in indexed:
            raise CensusError(f"duplicate result: {key}")
        indexed[key] = item
    comparisons = []
    missing = []
    profiles = _manifest_profiles(manifest)
    for profile in profiles:
        profile_id = str(profile.get("profile_id", profile.get("setting_id")))
        for game in manifest["selection"]["game_ids"]:
            control = indexed.get((profile_id, game, "r2_only"))
            shared = indexed.get((profile_id, game, "shared_attention_qwen"))
            if control is None or shared is None:
                missing.append({"profile_id": profile_id, "game": game})
                continue
            comparison = classify_pair(control, shared)
            comparisons.append({"profile_id": profile_id, "game": game, **comparison})
    if require_complete and missing:
        raise CensusError(f"missing paired results: {missing}")

    by_profile = []
    for profile in profiles:
        profile_id = str(profile.get("profile_id", profile.get("setting_id")))
        rows = [item for item in comparisons if item["profile_id"] == profile_id]
        gains = sum(item["bucket"] == "A" for item in rows)
        elapsed_overhead = sum(item["elapsed_overhead_s"] for item in rows)
        by_profile.append(
            {
                "profile_id": profile_id,
                "pairs": len(rows),
                "bucket_counts": dict(sorted(Counter(item["bucket"] for item in rows).items())),
                "completion_delta_total": sum(item["completion_delta"] for item in rows),
                "N_QR": sum(item["N_QR"] for item in rows),
                "N_RQ": sum(item["N_RQ"] for item in rows),
                "complete_causal_chains": sum(item["complete_causal_chains"] for item in rows),
                "meaningful_novelty": sum(item["meaningful_novelty"] for item in rows),
                "support_authority_violations": sum(
                    item["support_authority_violations"] for item in rows
                ),
                "harmful_pairs": sum(item["harmful"] for item in rows),
                "hard_level_regressions": sum(item["hard_level_regression"] for item in rows),
                "graph_native_pairs": sum(
                    item["telemetry_source"] == "graph_native" for item in rows
                ),
                "r_to_q_pickup_tasks": sum(item["r_to_q_pickup_tasks"] for item in rows),
                "q_to_r_pickup_tasks": sum(item["q_to_r_pickup_tasks"] for item in rows),
                "bidirectional_pickup_tasks": sum(item["bidirectional_pickup_tasks"] for item in rows),
                "qwen_calls": sum(item["qwen_calls"] for item in rows),
                "qwen_total_tokens": sum(item["qwen_total_tokens"] for item in rows),
                "shared_attention_elapsed_s": sum(item["shared_elapsed_s"] for item in rows),
                "r2_elapsed_s": sum(item["r2_elapsed_s"] for item in rows),
                "elapsed_overhead_s": elapsed_overhead,
                "seconds_overhead_per_task_gain": elapsed_overhead / gains if gains else None,
                "median_action_savings_fraction_when_comparable": (
                    statistics.median(
                        item["action_savings_fraction"]
                        for item in rows
                        if item["action_savings_fraction"] is not None
                    )
                    if any(item["action_savings_fraction"] is not None for item in rows)
                    else None
                ),
            }
        )

    primary_profile = str(
        manifest["paired_design"].get("primary_profile", "balanced")
    )
    primary_rows = [item for item in comparisons if item["profile_id"] == primary_profile]
    exact_primary = all(item["replay_valid"] and item["same_initial_observation"] for item in primary_rows)
    pickup_games = {
        item["game"] for item in primary_rows if item["N_QR"] > 0 or item["N_RQ"] > 0
    }
    mechanistically_present = (
        sum(item["N_QR"] for item in primary_rows) > 0
        and sum(item["N_RQ"] for item in primary_rows) > 0
        and len(pickup_games) >= 2
        and sum(item["support_authority_violations"] for item in primary_rows) == 0
        and exact_primary
    )
    control_promising = (
        mechanistically_present
        and any(item["bucket"] == "A" for item in primary_rows)
        and sum(item["hard_level_regression"] for item in primary_rows) <= 1
    )
    sensitivity_rows = [item for item in comparisons if item["profile_id"] != primary_profile]
    attention_bottleneck = (
        sum(item["meaningful_novelty"] for item in primary_rows) > 0
        and sum(item["N_QR"] + item["N_RQ"] for item in primary_rows) == 0
        and sum(item["N_QR"] + item["N_RQ"] for item in sensitivity_rows) > 0
    )
    valid_transport = all(
        item["replay_valid"]
        and item["same_initial_observation"]
        and item["qwen_context_valid"]
        and item["qwen_transport_successful"]
        for item in comparisons
    )
    representation_or_model_bottleneck = (
        bool(comparisons)
        and valid_transport
        and all(item["bucket"] in {"C", "D"} for item in comparisons)
    )
    if control_promising:
        verdict = "CONTROL_PROMISING"
    elif mechanistically_present:
        verdict = "MECHANISTICALLY_PRESENT"
    elif attention_bottleneck:
        verdict = "ATTENTION_BOTTLENECK"
    elif representation_or_model_bottleneck:
        verdict = "REPRESENTATION_OR_MODEL_BOTTLENECK"
    else:
        verdict = "INCONCLUSIVE"
    return {
        "protocol": PROTOCOL,
        "manifest_digest": manifest["manifest_digest"],
        "complete": not missing,
        "missing_pairs": missing,
        "bucket_definitions": {
            "A": "complete grounded Qwen-to-R2 causal chain plus paired task gain without hard regression",
            "B": "grounded bidirectional pickup without task gain",
            "C": "non-paraphrastic Qwen proposal without R2 pickup",
            "D": "no meaningful Qwen novelty",
            "INVALID": "failed replay, mismatched fresh start, or episode error; excluded from verdict",
        },
        "harmful_definition": (
            "separate flag for hard level regression, unsupported action influence, supported-R2 "
            "frontier crowd-out, or at least 25% more actions on comparable completion"
        ),
        "comparisons": comparisons,
        "profiles": by_profile,
        "settings": by_profile,
        "primary_profile": primary_profile,
        "verdict": verdict,
        "verdict_checks": {
            "mechanistically_present": mechanistically_present,
            "control_promising": control_promising,
            "attention_bottleneck": attention_bottleneck,
            "representation_or_model_bottleneck": representation_or_model_bottleneck,
            "primary_pickup_games": sorted(pickup_games),
            "primary_exact_replay": exact_primary,
        },
        "overall_bucket_counts": dict(sorted(Counter(item["bucket"] for item in comparisons).items())),
        "games_with_any_task_gain": sorted(
            {item["game"] for item in comparisons if item["bucket"] == "A"}
        ),
        "games_with_any_regression_or_invalidity": sorted(
            {
                item["game"]
                for item in comparisons
                if item["bucket"] == "INVALID" or item["hard_level_regression"]
            }
        ),
        "games_flagged_harmful": sorted(
            {item["game"] for item in comparisons if item["harmful"]}
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recordings", type=Path, default=DEFAULT_RECORDINGS)
    parser.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    parser.add_argument("--output", type=Path, default=HERE / "FROZEN_CENSUS_MANIFEST.json")
    args = parser.parse_args(argv)
    manifest = build_manifest(args.recordings, args.environments)
    write_manifest(
        args.output,
        {
            "protocol": manifest["protocol"],
            "game_ids": manifest["selection"]["game_ids"],
            "corpus_digest": manifest["selection"]["corpus_digest"],
            "manifest_digest": manifest["manifest_digest"],
            "job_count": len(manifest["jobs"]),
            "pair_count": len(manifest["jobs"]) // 2,
            "maximum_environment_actions": manifest["runtime_estimate"]["maximum_environment_actions"],
            "maximum_qwen_calls": manifest["runtime_estimate"]["maximum_qwen_calls"],
        },
    )
    print(json.dumps({
        "games": manifest["selection"]["game_ids"],
        "jobs": len(manifest["jobs"]),
        "manifest_digest": manifest["manifest_digest"],
        "runtime_estimate": manifest["runtime_estimate"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
