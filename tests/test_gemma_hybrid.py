import json

import pytest

from reflector.research.gemma_hybrid import GemmaHybridBrain


def test_gemma_response_requires_grounded_candidate_and_hypothesis() -> None:
    assert GemmaHybridBrain.parse_response(
        'prefix {"candidate":2,"hypothesis":"test inverse control"} suffix'
    ) == (2, "test inverse control")
    with pytest.raises(ValueError, match="integer"):
        GemmaHybridBrain.parse_response(
            json.dumps({"candidate": "2", "hypothesis": "bad"})
        )


def test_symbolic_summary_and_difference_are_content_grounded() -> None:
    before = ((0, 0, 0), (0, 7, 0), (0, 0, 0))
    after = ((0, 0, 0), (0, 0, 7), (0, 0, 0))

    summary = GemmaHybridBrain._summary(after)
    difference = GemmaHybridBrain._difference(before, after)

    assert summary["size"] == [3, 3]
    assert any(item["color"] == 7 for item in summary["components"])
    assert difference == {
        "available": True,
        "changed_cells": 2,
        "changed_bbox": [1, 1, 2, 1],
    }
