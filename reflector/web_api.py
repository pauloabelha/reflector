"""Local replay/analysis API; deliberately outside the Kaggle inference path."""

from __future__ import annotations

import json
import mimetypes
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .core.mind import MindConfig
from .evolution.experiments import ExperimentStore
from .runtime.policy import SymbolicPolicy
from .runtime.trace import EpisodeTrace

MAX_REQUEST_BYTES = 1_000_000


def _action_predictions(policy: SymbolicPolicy, action_id: int) -> list[dict[str, Any]]:
    return [
        {
            "event": event,
            "probability": policy.mind.schemas.event_probability(action_id, event),
        }
        for event in policy.mind.schemas.event_kinds(action_id)
    ]


def analyze_trace(
    trace: EpisodeTrace, config: MindConfig | None = None
) -> dict[str, Any]:
    """Reconstruct the symbolic state at every recorded decision."""

    deployed = (
        config
        if config is not None
        else (
            MindConfig.from_dict(trace.mind_config)
            if trace.mind_config
            else MindConfig()
        )
    )
    policy = SymbolicPolicy(deployed)
    steps: list[dict[str, Any]] = []
    for step in trace.steps:
        actual = policy.choose_action(step.observation)
        snapshot = policy.mind.snapshot()
        steps.append(
            {
                "index": step.index,
                "observation": step.observation.to_dict(),
                "scene": step.scene.to_dict(),
                "recorded_decision": step.decision.to_dict(),
                "replayed_decision": actual.to_dict(),
                "decision_matches": actual == step.decision,
                "incoming_transition": (
                    step.incoming_transition.to_dict()
                    if step.incoming_transition is not None
                    else None
                ),
                "predictions": _action_predictions(policy, actual.action_id),
                "new_concepts": list(step.new_concepts),
                "new_hypotheses": list(step.new_hypotheses),
                "new_abstractions": list(step.new_abstractions),
                "experiment": step.experiment,
                "plan_actions": list(step.plan_actions),
                "planner_expansions": step.planner_expansions,
                "symbolic_state": snapshot,
            }
        )
    if trace.terminal_observation is not None:
        policy.observe(trace.terminal_observation)
    return {
        "trace": {
            "format_version": trace.format_version,
            "agent_version": trace.agent_version,
            "step_count": len(trace.steps),
            "terminal": (
                {
                    "observation": trace.terminal_observation.to_dict(),
                    "scene": (
                        trace.terminal_scene.to_dict()
                        if trace.terminal_scene is not None
                        else None
                    ),
                    "transition": (
                        trace.terminal_transition.to_dict()
                        if trace.terminal_transition is not None
                        else None
                    ),
                }
                if trace.terminal_observation is not None
                else None
            ),
        },
        "config": policy.mind.config.to_dict(),
        "steps": steps,
        "final_symbolic_state": policy.mind.snapshot(),
    }


def branch_replay(
    trace: EpisodeTrace,
    *,
    from_step: int,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Replay a config branch over recorded observations.

    This cannot advance a counterfactual environment, so it reports policy
    divergence and predicted effects without claiming alternate game outcomes.
    """

    if not 0 <= from_step < len(trace.steps):
        raise ValueError("from_step is outside the trace")
    config_value = (
        dict(trace.mind_config)
        if trace.mind_config
        else MindConfig().to_dict()
    )
    config_value.update(patch)
    config = MindConfig.from_dict(config_value)
    analysis = analyze_trace(trace, config)
    branch_steps = analysis["steps"][from_step:]
    divergences = sum(
        not item["decision_matches"] for item in branch_steps
    )
    return {
        "mode": "trace-only-policy-branch",
        "limitation": (
            "Recorded observations are fixed; alternate actions do not generate "
            "counterfactual environment states or score claims."
        ),
        "from_step": from_step,
        "config": config.to_dict(),
        "divergences": divergences,
        "steps": branch_steps,
    }


@dataclass(frozen=True, slots=True)
class WebState:
    trace: EpisodeTrace
    database: Path | None
    static_directory: Path
    workspace: Path | None = None

    def experiments(self) -> list[dict[str, Any]]:
        if self.database is None or not self.database.exists():
            return []
        with ExperimentStore(self.database) as store:
            return list(store.list_experiments())

    def experiment(self, experiment_id: str) -> dict[str, Any]:
        if self.database is None or not self.database.exists():
            raise KeyError(experiment_id)
        with ExperimentStore(self.database) as store:
            return store.experiment_report(experiment_id)

    def live_snapshot(self) -> dict[str, Any]:
        return live_snapshot(self.workspace or self.static_directory.parent.parent)


def _tail_jsonl(path: Path, count: int = 40) -> list[dict[str, Any]]:
    """Read a bounded JSONL tail without loading a multi-megabyte stream."""

    with path.open("rb") as stream:
        stream.seek(0, 2)
        remaining = stream.tell()
        chunks: list[bytes] = []
        lines = 0
        while remaining and lines <= count:
            size = min(65_536, remaining)
            remaining -= size
            stream.seek(remaining)
            chunk = stream.read(size)
            chunks.append(chunk)
            lines += chunk.count(b"\n")
    output: list[dict[str, Any]] = []
    for line in b"".join(reversed(chunks)).splitlines()[-count:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            output.append(value)
    return output


def _scorecards(workspace: Path) -> list[tuple[Path, dict[str, Any]]]:
    reports = workspace / "reports"
    output: list[tuple[Path, dict[str, Any]]] = []
    if not reports.is_dir():
        return output
    for path in reports.rglob("*.json"):
        try:
            if path.stat().st_size > 30_000_000:
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            isinstance(value, dict)
            and isinstance(value.get("scorecard"), dict)
            and isinstance(value["scorecard"].get("environments"), list)
        ):
            output.append((path, value))
    return output


def _game_name(value: str) -> str:
    return value.split("-", 1)[0]


def _report_summary(path: Path, report: dict[str, Any], workspace: Path) -> dict[str, Any]:
    scorecard = report["scorecard"]
    environments = scorecard["environments"]
    return {
        "path": str(path.relative_to(workspace)),
        "name": path.parent.name if path.name == "official-report.json" else path.stem,
        "score": scorecard.get("score", 0),
        "levels_completed": scorecard.get("total_levels_completed", 0),
        "levels_total": scorecard.get("total_levels", 0),
        "games_completed": scorecard.get("total_environments_completed", 0),
        "games_total": scorecard.get("total_environments", len(environments)),
        "actions": scorecard.get("total_actions", 0),
        "modified": path.stat().st_mtime,
        "source_commit": report.get("source_commit"),
    }


def live_snapshot(workspace: Path) -> dict[str, Any]:
    """Summarize active streams and all local official score evidence."""

    workspace = workspace.resolve()
    now = time.time()
    scorecards = _scorecards(workspace)
    summaries = sorted(
        (_report_summary(path, report, workspace) for path, report in scorecards),
        key=lambda item: item["modified"],
        reverse=True,
    )
    full = [item for item in summaries if item["games_total"] >= 25]
    best_full = max(
        full,
        key=lambda item: (
            item["score"],
            item["levels_completed"],
            -item["actions"],
        ),
        default=None,
    )

    games: dict[str, dict[str, Any]] = {}
    for path, report in scorecards:
        report_name = path.parent.name if path.name == "official-report.json" else path.stem
        for environment in report["scorecard"]["environments"]:
            game = _game_name(str(environment.get("id", "")))
            if not game:
                continue
            levels_completed = int(environment.get("levels_completed", 0))
            game_score = float(environment.get("score", 0))
            actions = int(environment.get("actions", 0))
            item = {
                "game": game,
                "levels_completed": levels_completed,
                "levels_total": int(environment.get("level_count", 0)),
                "score": game_score,
                "actions": actions,
                "completed": bool(environment.get("completed", False)),
                "report": report_name,
                "level_actions": (
                    environment.get("runs", [{}])[0].get("level_actions", [])
                    if environment.get("runs")
                    else []
                ),
            }
            incumbent = games.get(game)
            item_rank = (levels_completed, game_score, -actions)
            incumbent_rank = (
                (
                    int(incumbent["levels_completed"]),
                    float(incumbent["score"]),
                    -int(incumbent["actions"]),
                )
                if incumbent is not None
                else None
            )
            if incumbent_rank is None or item_rank > incumbent_rank:
                games[game] = item

    streams = sorted(
        (workspace / "reports").glob("**/cognitive/*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if (workspace / "reports").is_dir() else []
    current: dict[str, Any] | None = None
    logs: list[dict[str, Any]] = []
    if streams:
        stream = streams[0]
        events = _tail_jsonl(stream)
        if events:
            event = events[-1]
            observation = event.get("observation", {})
            deployment = event.get("deployment", {})
            operative = event.get("operative_state", {})
            exploration = operative.get("exploration", {})
            diagnostics = {
                key: value
                for key, value in exploration.items()
                if (
                    key.endswith("_diagnostic")
                    or key.endswith("_confirmations")
                    or key.endswith("_conflicts")
                    or key.endswith("_predictions")
                    or key in {
                        "planner_expansions",
                        "states",
                        "frontier_states",
                        "inherited_scheme_count",
                        "inherited_scheme_selections",
                    }
                )
                and value not in (0, None, "", "not-attempted", "exact-off")
            }
            current = {
                "active": now - stream.stat().st_mtime < 8,
                "game": deployment.get("game_id", stream.stem),
                "candidate_id": deployment.get("candidate_id"),
                "agent_version": deployment.get("agent_version"),
                "inference_fingerprint": deployment.get("inference_fingerprint"),
                "level": observation.get("levels_completed", 0),
                "state": observation.get("state"),
                "action": event.get("decision"),
                "sequence": event.get("sequence"),
                "objects": observation.get("object_count"),
                "stream": str(stream.relative_to(workspace)),
                "modified": stream.stat().st_mtime,
                "diagnostics": diagnostics,
            }
            for item in events:
                transition = item.get("transition") or {}
                logs.append(
                    {
                        "sequence": item.get("sequence"),
                        "level": item.get("observation", {}).get("levels_completed"),
                        "state": item.get("observation", {}).get("state"),
                        "action_id": item.get("decision", {}).get("action_id"),
                        "reason": item.get("decision", {}).get("reason"),
                        "result": transition.get("result", []),
                        "new": {
                            key: len(item.get("construction_delta", {}).get(key, []))
                            for key in ("concepts", "hypotheses", "abstractions")
                        },
                    }
                )

    candidates = sorted(
        (workspace / "candidates").glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if (workspace / "candidates").is_dir() else []
    offspring = None
    if candidates:
        try:
            value = json.loads(candidates[0].read_text(encoding="utf-8"))
            offspring = {
                key: value.get(key)
                for key in (
                    "candidate_id",
                    "parent_id",
                    "generation",
                    "rationale",
                    "mutation_source",
                    "inference_fingerprint",
                )
            }
            offspring["path"] = str(candidates[0].relative_to(workspace))
        except (OSError, json.JSONDecodeError):
            pass

    artifacts = sorted(
        (
            path
            for path in (workspace / "reports").glob("**/*")
            if path.is_file() and path.suffix.lower() in {".md", ".json", ".png", ".svg"}
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:16] if (workspace / "reports").is_dir() else []
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace": str(workspace),
        "status": "running" if current and current["active"] else "idle",
        "current": current,
        "offspring": offspring,
        "best_full": best_full,
        "latest_run": summaries[0] if summaries else None,
        "runs": summaries[:12],
        "games": [games[key] for key in sorted(games)],
        "logs": logs,
        "artifacts": [
            {
                "path": str(path.relative_to(workspace)),
                "kind": path.suffix.lower().lstrip("."),
                "modified": path.stat().st_mtime,
            }
            for path in artifacts
        ],
    }


class ReflectorHTTPServer(ThreadingHTTPServer):
    state: WebState


class ReflectorRequestHandler(BaseHTTPRequestHandler):
    server: ReflectorHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                self._json({"status": "ok", "service": "reflector"})
            elif path == "/api/live":
                self._json(self.server.state.live_snapshot())
            elif path == "/api/live/events":
                self._live_events()
            elif path == "/api/replay":
                self._json(analyze_trace(self.server.state.trace))
            elif path == "/api/experiments":
                self._json({"experiments": self.server.state.experiments()})
            elif path.startswith("/api/experiments/"):
                experiment_id = unquote(path.removeprefix("/api/experiments/"))
                self._json(self.server.state.experiment(experiment_id))
            elif path.startswith("/api/"):
                self._error(HTTPStatus.NOT_FOUND, "unknown API route")
            else:
                self._static(path)
        except KeyError:
            self._error(HTTPStatus.NOT_FOUND, "experiment not found")
        except (TypeError, ValueError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/branch":
            self._error(HTTPStatus.NOT_FOUND, "unknown API route")
            return
        try:
            payload = self._request_json()
            if set(payload) != {"from_step", "patch"}:
                raise ValueError("branch body requires exactly from_step and patch")
            if type(payload["from_step"]) is not int:
                raise ValueError("from_step must be an integer")
            if not isinstance(payload["patch"], dict):
                raise ValueError("patch must be an object")
            self._json(
                branch_replay(
                    self.server.state.trace,
                    from_step=payload["from_step"],
                    patch=payload["patch"],
                )
            )
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _live_events(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                payload = json.dumps(
                    self.server.state.live_snapshot(),
                    separators=(",", ":"),
                )
                self.wfile.write(f"event: snapshot\ndata: {payload}\n\n".encode())
                self.wfile.flush()
                time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _request_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= MAX_REQUEST_BYTES:
            raise ValueError("invalid request body size")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("request body must be an object")
        return value

    def _json(
        self, value: Any, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(value, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json({"error": message}, status)

    def _static(self, request_path: str) -> None:
        root = self.server.state.static_directory.resolve()
        relative = "index.html" if request_path in ("", "/") else unquote(
            request_path.lstrip("/")
        )
        candidate = (root / relative).resolve()
        if root not in candidate.parents and candidate != root:
            self._error(HTTPStatus.NOT_FOUND, "asset not found")
            return
        if not candidate.is_file():
            # Client-side routes fall back to the application shell.
            candidate = root / "index.html"
        if not candidate.is_file():
            self._error(
                HTTPStatus.NOT_FOUND,
                "web build missing; run npm run build in web/",
            )
            return
        body = candidate.read_bytes()
        media_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(
    *,
    trace: EpisodeTrace,
    database: Path | None,
    static_directory: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    workspace: Path | None = None,
) -> ReflectorHTTPServer:
    server = ReflectorHTTPServer((host, port), ReflectorRequestHandler)
    server.state = WebState(trace, database, static_directory, workspace)
    return server


def serve(
    *,
    trace: EpisodeTrace,
    database: Path | None,
    static_directory: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    workspace: Path | None = None,
) -> None:
    server = create_server(
        trace=trace,
        database=database,
        static_directory=static_directory,
        host=host,
        port=port,
        workspace=workspace,
    )
    print(f"Reflector replay console: http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReflector replay console stopped.")
    finally:
        server.server_close()
