"""Process executed inside a network namespace by ``kaggle_smoke_test``."""

from __future__ import annotations

import sys
from pathlib import Path

from arc_agi import Arcade, OperationMode

from agents.templates.reflector_agent import ReflectorAgent


def main() -> None:
    environments = Path(sys.argv[1]).resolve()
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments),
        recordings_dir=str(environments.parent / "recordings"),
    )
    environment = arcade.make("bt11", include_frame_data=True)
    if environment is None:
        raise RuntimeError("official toolkit did not initialize bt11")

    # Execute the adapter extracted from the submission overlay, not a
    # test-specific copy of its decision logic.
    agent = ReflectorAgent(
        card_id=environment.scorecard_id,
        game_id="bt11",
        agent_name="reflector",
        ROOT_URL="http://gateway:8001",
        record=False,
        arc_env=environment,
    )
    observation = agent._convert_raw_frame_data(environment.observation_space)
    action = agent.choose_action([observation], observation)
    if (
        observation.state.value == "NOT_FINISHED"
        and action.value not in observation.available_actions
    ):
        raise AssertionError(f"illegal action selected: {action.value}")
    advanced = agent.take_action(action)
    if advanced is None:
        raise AssertionError("official environment did not advance")
    agent.append_frame(advanced)
    agent.cleanup()
    arcade.close_scorecard()
    print(
        "kaggle_smoke_test: PASS "
        f"(action={action.value}, state={advanced.state.value})"
    )


if __name__ == "__main__":
    main()
