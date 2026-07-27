import pytest

from reflector.kaggle import smoke_test


@pytest.mark.integration
def test_packaged_submission_with_network_disabled() -> None:
    smoke_test()
