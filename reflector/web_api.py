"""Local replay/analysis API; deliberately outside the Kaggle inference path."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .experiments import ExperimentStore
from .mind import MindConfig
from .policy import SymbolicPolicy
from .trace import EpisodeTrace

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


class ReflectorHTTPServer(ThreadingHTTPServer):
    state: WebState


class ReflectorRequestHandler(BaseHTTPRequestHandler):
    server: ReflectorHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                self._json({"status": "ok", "service": "reflector"})
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
        self.wfile.write(body)

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
) -> ReflectorHTTPServer:
    server = ReflectorHTTPServer((host, port), ReflectorRequestHandler)
    server.state = WebState(trace, database, static_directory)
    return server


def serve(
    *,
    trace: EpisodeTrace,
    database: Path | None,
    static_directory: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    server = create_server(
        trace=trace,
        database=database,
        static_directory=static_directory,
        host=host,
        port=port,
    )
    print(f"Reflector replay console: http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReflector replay console stopped.")
    finally:
        server.server_close()
