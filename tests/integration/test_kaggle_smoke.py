import pytest

from reflector.kaggle import smoke_test
from reflector.mind import MindConfig


@pytest.mark.integration
def test_packaged_submission_with_network_disabled() -> None:
    smoke_test()


@pytest.mark.integration
def test_selected_descendant_with_network_disabled() -> None:
    smoke_test(
        MindConfig(
            planner_max_expansions=17,
            information_weight=2.5,
        )
    )
