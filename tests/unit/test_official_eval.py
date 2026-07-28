from pathlib import Path

import pytest

from reflector.official_eval import (
    expected_public_game_count,
    inventory_official_environments,
)

ROOT = Path(__file__).resolve().parents[2]


def test_official_inventory_hashes_fixture_and_requires_exact_coverage() -> None:
    inventory = inventory_official_environments(
        ROOT / "tests" / "fixtures" / "official_toolkit",
        expected_games=1,
    )
    assert inventory.games == ("bt11",)
    assert len(inventory.artifacts) == 1
    assert inventory.artifacts[0].versioned_game_id.startswith("bt11-")
    assert len(inventory.artifacts[0].metadata_sha256) == 64
    assert len(inventory.manifest_sha256) == 64

    with pytest.raises(ValueError, match="expected 25.*found 1"):
        inventory_official_environments(
            ROOT / "tests" / "fixtures" / "official_toolkit",
            expected_games=25,
        )


def test_rules_snapshot_drives_public_game_count() -> None:
    assert expected_public_game_count(ROOT) == 25
