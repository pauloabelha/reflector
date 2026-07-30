import json
from pathlib import Path

import pytest

from scripts.generate_level_matrix import load_game_levels


def test_level_matrix_loads_the_accepted_v69_scorecard() -> None:
    rows = load_game_levels()

    assert len(rows) == 25
    assert sum(row.completed for row in rows) == 30
    assert sum(row.total for row in rows) == 183
    assert next(row for row in rows if row.game == "lp85").completed == 5
    assert next(row for row in rows if row.game == "cd82").completed == 2


def test_level_matrix_rejects_impossible_counts(tmp_path: Path) -> None:
    scorecard = tmp_path / "scorecard.json"
    scorecard.write_text(
        json.dumps(
            {
                "scorecard": {
                    "environments": [
                        {
                            "id": "test-deadbeef",
                            "levels_completed": 2,
                            "level_count": 1,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="impossible level count"):
        load_game_levels(scorecard)
