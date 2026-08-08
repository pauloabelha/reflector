from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

from reflector2.arc_harness import (
    ArcGameSession,
    JsonlTrace,
    discover_game_ids,
    normalize_observation,
    run_suite,
)
from reflector2.perception import PerceptionBatch
from reflector2.runtime import Runtime


class State(str, Enum):
    NOT_PLAYED = "NOT_PLAYED"
    NOT_FINISHED = "NOT_FINISHED"
    WIN = "WIN"
    GAME_OVER = "GAME_OVER"


class SimpleAction:
    model_fields: dict[str, object] = {}


class ComplexAction:
    model_fields = {"x": object(), "y": object()}


@dataclass(frozen=True)
class FakeAction:
    value: int
    complex: bool = False

    @property
    def action_type(self):
        return ComplexAction if self.complex else SimpleAction

    def is_complex(self) -> bool:
        return self.complex

    def validate_data(self, data: dict[str, int]) -> bool:
        assert set(data) == {"x", "y"}
        return True


ACTIONS = {
    0: FakeAction(0),
    1: FakeAction(1),
    6: FakeAction(6, complex=True),
}


@dataclass
class Raw:
    game_id: str
    frame: object
    state: State = State.NOT_FINISHED
    levels_completed: int = 0
    win_levels: int = 2
    full_reset: bool = False
    available_actions: tuple[int, ...] = (1, 6)
    reward: float | None = None


GRID_A = (
    (0, 0, 0, 0),
    (0, 2, 2, 0),
    (0, 0, 0, 0),
)
GRID_B = (
    (0, 0, 0, 0),
    (0, 3, 3, 0),
    (0, 0, 0, 0),
)


class FakeEnvironment:
    def __init__(self, game_id: str = "fake-v1") -> None:
        self.game_id = game_id
        self.observation_space = Raw(
            game_id,
            [GRID_A, GRID_B],
            full_reset=True,
        )
        self.actions: list[tuple[int, dict[str, int]]] = []
        self.reset_count = 0

    @property
    def action_space(self) -> list[FakeAction]:
        return [ACTIONS[item] for item in self.observation_space.available_actions]

    def step(self, action: FakeAction, *, data: dict[str, int]):
        self.actions.append((action.value, data))
        self.observation_space = Raw(
            self.game_id,
            [GRID_B],
            state=State.WIN,
            levels_completed=2,
            available_actions=(),
            reward=1.5,
        )
        return self.observation_space

    def reset(self):
        self.reset_count += 1
        self.observation_space = Raw(
            self.game_id,
            [GRID_A],
            state=State.NOT_FINISHED,
            full_reset=True,
        )
        return self.observation_space


def test_observation_normalizes_layer_packet_to_ordered_r2_supports() -> None:
    runtime = Runtime()
    observation = normalize_observation(
        Raw("ordered-v1", [GRID_A, GRID_B], available_actions=(6, 1)),
        runtime,
        observation_id=3,
        episode=2,
    )

    assert [support.ordinal for support in observation.supports] == [0, 1]
    assert [support.grid for support in observation.supports] == [GRID_A, GRID_B]
    assert [action.action_id for action in observation.legal_actions] == [6, 1]
    assert observation.final_support.batch.context.endswith("observation:3:support:1")
    assert all(support.batch.facts for support in observation.supports)


def test_random_action_successor_updates_r2_and_emits_provenance(
    tmp_path: Path,
) -> None:
    environment = FakeEnvironment()
    runtime = Runtime()
    sink = JsonlTrace(tmp_path / "fake.trace.jsonl")
    result = ArcGameSession(
        environment,
        requested_game_id="fake-v1",
        runtime=runtime,
        random_seed=7,
        environment_seed=11,
        max_transitions=3,
        trace=sink,
        action_from_id=ACTIONS.__getitem__,
    ).run()

    assert result.completed
    assert result.transitions == 1
    assert result.random_actions == 1
    assert runtime.cycle == 2
    assert [event["event"] for event in sink.events] == [
        "observation",
        "transition",
        "observation",
    ]
    transition = sink.events[1]
    assert transition["before"] == 0
    assert transition["after"] == 1
    assert transition["action"]["id"] in {1, 6}
    assert transition["progress_delta"] == 2
    assert transition["environment_reward"] == 1.5
    assert transition["r2_event_end"] > transition["r2_event_start"]
    assert any(event["event"] == "mapping-evidence" for event in runtime.trace)
    assert (
        json.loads((tmp_path / "fake.trace.jsonl").read_text().splitlines()[1])[
            "r2_morphism"
        ]
        == transition["r2_morphism"]
    )


def test_seed_replays_action_and_complex_payload_exactly(tmp_path: Path) -> None:
    def play(path: Path):
        environment = FakeEnvironment()
        sink = JsonlTrace(path)
        ArcGameSession(
            environment,
            requested_game_id="fake-v1",
            runtime=Runtime(),
            random_seed=0,
            environment_seed=0,
            max_transitions=1,
            trace=sink,
            action_from_id=ACTIONS.__getitem__,
        ).run()
        return environment.actions, sink.events[1]["action"]

    assert play(tmp_path / "one.jsonl") == play(tmp_path / "two.jsonl")


def test_game_over_forces_reset_with_opaque_reset_provenance(tmp_path: Path) -> None:
    environment = FakeEnvironment()
    environment.observation_space = Raw(
        "fake-v1",
        [GRID_A],
        state=State.GAME_OVER,
        available_actions=(),
    )
    sink = JsonlTrace(tmp_path / "reset.jsonl")
    result = ArcGameSession(
        environment,
        requested_game_id="fake-v1",
        runtime=Runtime(),
        random_seed=2,
        environment_seed=3,
        max_transitions=1,
        trace=sink,
        action_from_id=ACTIONS.__getitem__,
    ).run()

    assert result.resets == 1
    assert result.random_actions == 0
    assert environment.reset_count == 1
    assert sink.events[1]["forced_reset"] is True
    assert sink.events[1]["action"] == {"id": 0, "token": "arc-action:0", "data": {}}


def test_transition_without_visual_correspondence_still_updates_r2() -> None:
    runtime = Runtime()
    before = PerceptionBatch("before", (), (), ())
    after = PerceptionBatch("after", (), (), ())

    schema_id = runtime.learn_transition(before, after, "arc-action:7")

    assert schema_id >= 0
    event = runtime.trace[-1]
    assert event["event"] == "mapping-evidence"
    assert event["before"] == "before"
    assert event["action"] == "arc-action:7"
    assert event["after"] == "after"
    assert event["correspondences"] == 0


class FakeScorecard:
    def __init__(self, game_ids: list[str]) -> None:
        self.score = 12.5
        self.environments = [
            SimpleNamespace(id=game_id, score=float(index + 1))
            for index, game_id in enumerate(game_ids)
        ]


class FakeArcade:
    def __init__(self) -> None:
        self.available_environments = [
            SimpleNamespace(game_id="z-v2"),
            SimpleNamespace(game_id="a-v1"),
        ]
        self.made: list[str] = []

    def open_scorecard(self, **_kwargs) -> str:
        return "card"

    def make(self, game_id: str, **_kwargs):
        self.made.append(game_id)
        return FakeEnvironment(game_id)

    def close_scorecard(self, card_id: str) -> FakeScorecard:
        assert card_id == "card"
        return FakeScorecard(self.made)


def test_suite_discovers_games_scores_and_writes_both_trace_layers(
    tmp_path: Path,
) -> None:
    arcade = FakeArcade()
    assert discover_game_ids(arcade) == ("a-v1", "z-v2")
    summary = run_suite(
        arcade,
        games=None,
        seed=42,
        max_transitions=1,
        trace_dir=tmp_path,
        action_from_id=ACTIONS.__getitem__,
        expected_games=2,
        include_grids=False,
    )

    assert summary["errors"] == []
    assert summary["games_completed_without_error"] == 2
    assert [game["score"] for game in summary["games"]] == [1.0, 2.0]
    assert (tmp_path / "a-v1.trace.jsonl").is_file()
    assert (tmp_path / "a-v1.r2.jsonl").is_file()
    assert json.loads((tmp_path / "summary.json").read_text())["seed"] == 42
