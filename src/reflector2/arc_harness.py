"""Thin ARC-AGI-3 environment adapter and reproducible random baseline.

The module deliberately knows only the public toolkit transport contract.  It
does not name games, interpret action identities, or contain a solving policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast

from .perception import Grid, PerceptionBatch, perceive_grid
from .runtime import Runtime


class EnvironmentTransport(Protocol):
    observation_space: object | None

    @property
    def action_space(self) -> Sequence[object]: ...

    def reset(self) -> object | None: ...

    def step(self, action: object, *, data: dict[str, int]) -> object | None: ...


class ArcadeTransport(Protocol):
    available_environments: Sequence[object]

    def open_scorecard(self, **kwargs: object) -> str: ...

    def make(self, game_id: str, **kwargs: object) -> object | None: ...

    def close_scorecard(self, card_id: str) -> object | None: ...


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _state_name(value: object) -> str:
    return str(_enum_value(value))


def _action_id(value: object) -> int:
    action_id = _enum_value(value)
    if type(action_id) is not int:
        raise TypeError(f"ARC action identity must be an integer, got {action_id!r}")
    return action_id


def _grid(value: object) -> Grid:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("ARC support must be a non-empty rectangular grid")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw_row in value:
        if hasattr(raw_row, "tolist"):
            raw_row = raw_row.tolist()
        if (
            not isinstance(raw_row, Sequence)
            or isinstance(raw_row, (str, bytes))
            or not raw_row
        ):
            raise ValueError("ARC support must be a non-empty rectangular grid")
        row = tuple(int(cell) for cell in raw_row)
        if width is None:
            width = len(row)
        if len(row) != width:
            raise ValueError("ARC support must be a non-empty rectangular grid")
        rows.append(row)
    return tuple(rows)


def _ordered_grids(frame: object) -> tuple[Grid, ...]:
    """Normalize either a single grid or an ordered toolkit layer packet."""

    if hasattr(frame, "tolist"):
        frame = frame.tolist()
    if not isinstance(frame, Sequence) or isinstance(frame, (str, bytes)) or not frame:
        raise ValueError("ARC observation has no frame supports")
    first = frame[0]
    if hasattr(first, "tolist"):
        first = first.tolist()
    if not isinstance(first, Sequence) or isinstance(first, (str, bytes)) or not first:
        raise ValueError("ARC observation has no frame supports")
    first_cell = first[0]
    # Scalar at depth two means ``frame`` itself is one grid.  A nested row at
    # depth two means the toolkit supplied an ordered packet of grid supports.
    layers: Iterable[object] = (
        (frame,) if not isinstance(first_cell, Sequence) else frame
    )
    return tuple(_grid(layer) for layer in layers)


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _derived_seed(master_seed: int, game_id: str, stream: str) -> int:
    digest = hashlib.sha256(
        f"reflector2-arc-random-v1\0{master_seed}\0{game_id}\0{stream}".encode()
    ).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass(frozen=True, slots=True)
class OpaqueAction:
    """Transport identity only; the adapter assigns no action semantics."""

    action_id: int
    token: str

    @classmethod
    def from_id(cls, action_id: int) -> "OpaqueAction":
        return cls(action_id=action_id, token=f"arc-action:{action_id}")

    def to_dict(self) -> dict[str, object]:
        return {"id": self.action_id, "token": self.token}


@dataclass(frozen=True, slots=True)
class OrderedSupport:
    ordinal: int
    grid: Grid
    digest: str
    batch: PerceptionBatch = field(repr=False, compare=False)

    def to_dict(self, *, include_grid: bool) -> dict[str, object]:
        value: dict[str, object] = {
            "ordinal": self.ordinal,
            "digest": self.digest,
            "shape": [len(self.grid), len(self.grid[0])],
            "facts": len(self.batch.facts),
            "context": self.batch.context,
        }
        if include_grid:
            value["grid"] = [list(row) for row in self.grid]
        return value


@dataclass(frozen=True, slots=True)
class ArcObservation:
    observation_id: int
    game_id: str
    state: str
    levels_completed: int
    win_levels: int
    full_reset: bool
    reward: int | float | None
    legal_actions: tuple[OpaqueAction, ...]
    supports: tuple[OrderedSupport, ...]
    digest: str

    @property
    def final_support(self) -> OrderedSupport:
        return self.supports[-1]

    @property
    def complete(self) -> bool:
        return self.state == "WIN"

    def to_dict(self, *, include_grid: bool) -> dict[str, object]:
        return {
            "event": "observation",
            "observation": self.observation_id,
            "game_id": self.game_id,
            "state": self.state,
            "levels_completed": self.levels_completed,
            "win_levels": self.win_levels,
            "full_reset": self.full_reset,
            "reward": self.reward,
            "legal_actions": [action.to_dict() for action in self.legal_actions],
            "supports": [
                support.to_dict(include_grid=include_grid) for support in self.supports
            ],
            "digest": self.digest,
        }


def normalize_observation(
    raw: object,
    runtime: Runtime,
    *,
    observation_id: int,
    episode: int,
) -> ArcObservation:
    """Convert a toolkit observation to ordered R2 sensory supports."""

    game_id = str(getattr(raw, "game_id", ""))
    if not game_id:
        raise ValueError("ARC observation has no game_id")
    state = _state_name(getattr(raw, "state", ""))
    levels_completed = int(getattr(raw, "levels_completed", 0))
    win_levels = int(getattr(raw, "win_levels", 0))
    full_reset = bool(getattr(raw, "full_reset", False))
    raw_reward = getattr(raw, "reward", None)
    reward = raw_reward if isinstance(raw_reward, (int, float)) else None
    legal_ids = tuple(
        _action_id(item) for item in getattr(raw, "available_actions", ())
    )
    grids = _ordered_grids(getattr(raw, "frame", ()))
    supports: list[OrderedSupport] = []
    for ordinal, grid in enumerate(grids):
        context = (
            f"arc:{game_id}:episode:{episode}:observation:{observation_id}:"
            f"support:{ordinal}"
        )
        batch = perceive_grid(
            runtime.graph.terms,
            grid,
            context,
        )
        supports.append(
            OrderedSupport(
                ordinal=ordinal,
                grid=grid,
                digest=_digest(grid),
                batch=batch,
            )
        )
    digest = _digest(
        {
            "game_id": game_id,
            "state": state,
            "levels_completed": levels_completed,
            "win_levels": win_levels,
            "full_reset": full_reset,
            "legal_actions": legal_ids,
            "supports": [support.digest for support in supports],
        }
    )
    return ArcObservation(
        observation_id=observation_id,
        game_id=game_id,
        state=state,
        levels_completed=levels_completed,
        win_levels=win_levels,
        full_reset=full_reset,
        reward=reward,
        legal_actions=tuple(OpaqueAction.from_id(item) for item in legal_ids),
        supports=tuple(supports),
        digest=digest,
    )


class JsonlTrace:
    """Immediate, deterministic JSONL trace emission."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.events: list[dict[str, object]] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def emit(self, event: dict[str, object]) -> None:
        self.events.append(event)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
                stream.write("\n")


@dataclass(frozen=True, slots=True)
class GameRunResult:
    requested_game_id: str
    game_id: str
    random_seed: int
    environment_seed: int
    transitions: int
    random_actions: int
    resets: int
    levels_completed: int
    peak_levels_completed: int
    win_levels: int
    progress: float
    completed: bool
    final_state: str
    score: float | None
    runtime: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_game_id": self.requested_game_id,
            "game_id": self.game_id,
            "random_seed": self.random_seed,
            "environment_seed": self.environment_seed,
            "transitions": self.transitions,
            "random_actions": self.random_actions,
            "resets": self.resets,
            "levels_completed": self.levels_completed,
            "peak_levels_completed": self.peak_levels_completed,
            "win_levels": self.win_levels,
            "progress": self.progress,
            "completed": self.completed,
            "final_state": self.final_state,
            "score": self.score,
            "runtime": self.runtime,
        }


class ArcGameSession:
    """One environment, one R2 runtime, and one uniform-random controller."""

    def __init__(
        self,
        environment: EnvironmentTransport,
        *,
        requested_game_id: str,
        runtime: Runtime,
        random_seed: int,
        environment_seed: int,
        max_transitions: int,
        trace: JsonlTrace,
        action_from_id: Callable[[int], object],
        include_grids: bool = True,
    ) -> None:
        self.environment = environment
        self.requested_game_id = requested_game_id
        self.runtime = runtime
        self.random_seed = random_seed
        self.environment_seed = environment_seed
        self.max_transitions = max_transitions
        self.trace = trace
        self.action_from_id = action_from_id
        self.include_grids = include_grids
        self.rng = random.Random(random_seed)
        self.episode = 0

    def _observe(self, raw: object, observation_id: int) -> ArcObservation:
        observation = normalize_observation(
            raw,
            self.runtime,
            observation_id=observation_id,
            episode=self.episode,
        )
        self.runtime.observe(observation.final_support.batch)
        self.trace.emit(observation.to_dict(include_grid=self.include_grids))
        return observation

    def _legal_transport_actions(
        self, observation: ArcObservation
    ) -> tuple[tuple[OpaqueAction, object], ...]:
        by_id: dict[int, object] = {}
        for item in getattr(self.environment, "action_space", ()):
            by_id[_action_id(item)] = item
        output = []
        for opaque in observation.legal_actions:
            transport = by_id.get(opaque.action_id)
            if transport is None:
                transport = self.action_from_id(opaque.action_id)
            output.append((opaque, transport))
        return tuple(sorted(output, key=lambda item: item[0].action_id))

    def _sample_data(
        self, transport: object, support: OrderedSupport
    ) -> dict[str, int]:
        is_complex = getattr(transport, "is_complex", None)
        if not callable(is_complex) or not bool(is_complex()):
            return {}
        action_type = getattr(transport, "action_type", None)
        fields = set(getattr(action_type, "model_fields", {}))
        # arcengine's ComplexAction also carries an optional game_id transport
        # field. The wrapper/game supplies identity separately, so only x/y
        # need sampling here.
        if not {"x", "y"} <= fields or not fields <= {"game_id", "x", "y"}:
            raise ValueError(
                "unsupported ARC complex-action transport schema: "
                f"{sorted(str(field) for field in fields)}"
            )
        height, width = len(support.grid), len(support.grid[0])
        data = {"x": self.rng.randrange(width), "y": self.rng.randrange(height)}
        validate = getattr(transport, "validate_data", None)
        if callable(validate):
            validate(data)
        return data

    def _choose(
        self, observation: ArcObservation
    ) -> tuple[OpaqueAction, object, dict[str, int], bool]:
        if observation.state in {"NOT_PLAYED", "GAME_OVER"}:
            opaque = OpaqueAction.from_id(0)
            return opaque, self.action_from_id(0), {}, True
        legal = self._legal_transport_actions(observation)
        if not legal:
            raise RuntimeError(
                f"{observation.game_id} exposed no legal actions in {observation.state}"
            )
        opaque, transport = self.rng.choice(legal)
        return (
            opaque,
            transport,
            self._sample_data(transport, observation.final_support),
            False,
        )

    def run(self) -> GameRunResult:
        raw = getattr(self.environment, "observation_space", None)
        if raw is None:
            raw = self.environment.reset()
        if raw is None:
            raise RuntimeError(
                f"{self.requested_game_id} produced no initial observation"
            )
        current = self._observe(raw, 0)
        peak_levels = current.levels_completed
        random_actions = 0
        resets = 0
        transitions = 0

        while transitions < self.max_transitions and not current.complete:
            opaque, transport, data, forced_reset = self._choose(current)
            r2_start = len(self.runtime.trace)
            if forced_reset:
                successor_raw = self.environment.reset()
                resets += 1
                self.episode += 1
            else:
                successor_raw = self.environment.step(transport, data=data)
                random_actions += 1
            if successor_raw is None:
                raise RuntimeError(
                    f"{current.game_id} returned no successor for {opaque.token}"
                )
            successor = normalize_observation(
                successor_raw,
                self.runtime,
                observation_id=current.observation_id + 1,
                episode=self.episode,
            )
            self.runtime.observe(successor.final_support.batch)
            morphism_id = self.runtime.learn_transition(
                current.final_support.batch,
                successor.final_support.batch,
                opaque.token,
            )
            transitions += 1
            progress_delta = successor.levels_completed - current.levels_completed
            peak_levels = max(peak_levels, successor.levels_completed)
            self.trace.emit(
                {
                    "event": "transition",
                    "transition": transitions - 1,
                    "before": current.observation_id,
                    "before_digest": current.digest,
                    "action": {**opaque.to_dict(), "data": data},
                    "after": successor.observation_id,
                    "after_digest": successor.digest,
                    "forced_reset": forced_reset,
                    "reset_boundary": forced_reset or successor.full_reset,
                    "level_boundary": progress_delta != 0,
                    "progress_delta": progress_delta,
                    "environment_reward": successor.reward,
                    "completed": successor.complete,
                    "r2_morphism": self.runtime.graph.canonical_hash[morphism_id],
                    "r2_event_start": r2_start,
                    "r2_event_end": len(self.runtime.trace),
                }
            )
            self.trace.emit(successor.to_dict(include_grid=self.include_grids))
            current = successor

        deterministic_metrics = self.runtime.metrics.deterministic()
        runtime_report: dict[str, object] = {
            "cycles": self.runtime.cycle,
            "schemas": self.runtime.graph.schema_count,
            "active_shadows": len(
                [
                    shadow
                    for shadow in self.runtime.shadows.values()
                    if shadow.status == "SHADOW"
                ]
            ),
            "metrics": deterministic_metrics,
        }
        return GameRunResult(
            requested_game_id=self.requested_game_id,
            game_id=current.game_id,
            random_seed=self.random_seed,
            environment_seed=self.environment_seed,
            transitions=transitions,
            random_actions=random_actions,
            resets=resets,
            levels_completed=current.levels_completed,
            peak_levels_completed=peak_levels,
            win_levels=current.win_levels,
            progress=(peak_levels / current.win_levels if current.win_levels else 0.0),
            completed=current.complete,
            final_state=current.state,
            score=None,
            runtime=runtime_report,
        )


def discover_game_ids(arcade: ArcadeTransport) -> tuple[str, ...]:
    """Return exact local/public version identities in deterministic order."""

    game_ids = {
        str(getattr(info, "game_id"))
        for info in getattr(arcade, "available_environments", ())
        if getattr(info, "game_id", None)
    }
    return tuple(sorted(game_ids))


def _score_by_game(scorecard: object | None) -> dict[str, float]:
    if scorecard is None:
        return {}
    output: dict[str, float] = {}
    for environment in getattr(scorecard, "environments", ()):
        game_id = str(getattr(environment, "id", ""))
        score = getattr(environment, "score", None)
        if game_id and isinstance(score, (int, float)):
            output[game_id] = float(score)
    return output


def run_suite(
    arcade: ArcadeTransport,
    *,
    games: Sequence[str] | None,
    seed: int,
    max_transitions: int,
    trace_dir: Path,
    action_from_id: Callable[[int], object],
    expected_games: int | None = None,
    include_grids: bool = True,
) -> dict[str, object]:
    """Run isolated R2 runtimes under one official toolkit scorecard."""

    selected = tuple(games) if games else discover_game_ids(arcade)
    if expected_games is not None and len(selected) != expected_games:
        raise ValueError(
            f"expected {expected_games} ARC games, discovered/selected {len(selected)}"
        )
    trace_dir.mkdir(parents=True, exist_ok=True)
    card_id = arcade.open_scorecard(
        tags=["reflector2", "uniform-random", f"seed-{seed}"]
    )
    results: list[GameRunResult] = []
    errors: list[dict[str, str]] = []
    runtimes: dict[str, Runtime] = {}
    try:
        for requested_game_id in selected:
            random_seed = _derived_seed(seed, requested_game_id, "actions")
            environment_seed = _derived_seed(seed, requested_game_id, "environment")
            raw_environment = arcade.make(
                requested_game_id,
                seed=environment_seed,
                scorecard_id=card_id,
                include_frame_data=True,
            )
            if raw_environment is None:
                errors.append(
                    {"game_id": requested_game_id, "error": "environment did not load"}
                )
                continue
            environment = cast(EnvironmentTransport, raw_environment)
            runtime = Runtime()
            runtimes[requested_game_id] = runtime
            trace = JsonlTrace(trace_dir / f"{requested_game_id}.trace.jsonl")
            try:
                result = ArcGameSession(
                    environment,
                    requested_game_id=requested_game_id,
                    runtime=runtime,
                    random_seed=random_seed,
                    environment_seed=environment_seed,
                    max_transitions=max_transitions,
                    trace=trace,
                    action_from_id=action_from_id,
                    include_grids=include_grids,
                ).run()
                results.append(result)
            except Exception as error:  # keep suite coverage visible in the summary
                errors.append(
                    {
                        "game_id": requested_game_id,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
    finally:
        scorecard = arcade.close_scorecard(card_id)

    scores = _score_by_game(scorecard)
    game_results = []
    for requested_game_id, runtime in runtimes.items():
        r2_path = trace_dir / f"{requested_game_id}.r2.jsonl"
        with r2_path.open("w", encoding="utf-8") as stream:
            for event in runtime.trace:
                stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
                stream.write("\n")

    for result in results:
        value = result.to_dict()
        value["score"] = scores.get(result.game_id)
        game_results.append(value)

    summary: dict[str, object] = {
        "adapter": "reflector2-arc-harness/v1",
        "policy": "uniform-random-legal-action",
        "seed": seed,
        "max_transitions_per_game": max_transitions,
        "games_requested": len(selected),
        "games_completed_without_error": len(game_results),
        "errors": errors,
        "games": game_results,
        "score": (
            float(getattr(scorecard, "score"))
            if scorecard is not None
            and isinstance(getattr(scorecard, "score", None), (int, float))
            else None
        ),
        "total_levels_completed": sum(
            result.peak_levels_completed for result in results
        ),
        "total_transitions": sum(result.transitions for result in results),
    }
    (trace_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def _official_arcade(
    environments_dir: Path, recordings_dir: Path
) -> tuple[ArcadeTransport, Callable[[int], object]]:
    try:
        from arc_agi import Arcade, OperationMode  # type: ignore[import-untyped]
        from arcengine import GameAction  # type: ignore[import-untyped]
    except ImportError as error:  # pragma: no cover - exercised by installed CLI
        raise RuntimeError(
            "the ARC harness requires the project dependency arc-agi==0.9.9"
        ) from error
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments_dir),
        recordings_dir=str(recordings_dir),
    )
    return cast(ArcadeTransport, arcade), GameAction.from_id


def _parse_games(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        item.strip() for value in values for item in value.split(",") if item.strip()
    )


def _default_environments_dir() -> Path:
    repository_bundle = Path(__file__).resolve().parents[2] / "environment_files"
    return repository_bundle if repository_bundle.is_dir() else Path("environment_files")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environments-dir", type=Path, default=_default_environments_dir()
    )
    parser.add_argument("--recordings-dir", type=Path, default=Path("recordings"))
    parser.add_argument("--trace-dir", type=Path, default=Path("arc-traces"))
    parser.add_argument(
        "--game", action="append", default=[], help="game ID; repeat or comma-separate"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-transitions", type=int, default=80)
    parser.add_argument("--expected-games", type=int)
    parser.add_argument("--omit-grids", action="store_true")
    args = parser.parse_args()
    if args.max_transitions < 0:
        parser.error("--max-transitions must be non-negative")
    arcade, action_from_id = _official_arcade(
        args.environments_dir, args.recordings_dir
    )
    summary = run_suite(
        arcade,
        games=_parse_games(args.game) or None,
        seed=args.seed,
        max_transitions=args.max_transitions,
        trace_dir=args.trace_dir,
        action_from_id=action_from_id,
        expected_games=args.expected_games,
        include_grids=not args.omit_grids,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
