import json
import time
from pathlib import Path

import pytest

from agents import Swarm


@pytest.mark.integration
def test_official_swarm_runs_reflector_to_clean_termination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = (
        Path(__file__).parents[1] / "fixtures" / "official_toolkit"
    ).resolve()
    monkeypatch.setenv("OPERATION_MODE", "offline")
    monkeypatch.setenv("ENVIRONMENTS_DIR", str(fixture))
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path / "recordings"))

    swarm = Swarm(
        agent="reflector",
        ROOT_URL="http://localhost:8001",
        games=["bt11"],
    )
    scorecard = swarm.main()

    assert scorecard is not None
    assert scorecard.environments[0].levels_completed == 5
    assert scorecard.score == 100.0
    policy = swarm.agents[0].policy
    assert policy.trace.terminal_observation is not None
    assert policy.trace.terminal_observation.state == "WIN"

    duration = swarm.agents[0].seconds
    time.sleep(0.01)
    assert swarm.agents[0].seconds == duration

    recordings = list((tmp_path / "recordings").glob("*.recording.jsonl"))
    assert len(recordings) == 1
    frames = [
        json.loads(line)["data"]
        for line in recordings[0].read_text(encoding="utf-8").splitlines()
        if line
    ]
    actions = [
        frame["action_input"]
        for frame in frames
        if isinstance(frame, dict) and "action_input" in frame
    ]
    assert actions
    assert any(action["id"] != 0 for action in actions)
    assert any(
        action["reasoning"]["policy"].startswith("reflector-symbolic-")
        for action in actions
        if action["reasoning"] is not None
    )
