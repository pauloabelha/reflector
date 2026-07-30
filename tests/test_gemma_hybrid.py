import json

import pytest

from reflector.core.mind import MindConfig
from reflector.core.symbolic import Decision, Observation
from reflector.research.gemma_hybrid import (
    GemmaAugmentedSymbolicPolicy,
    GemmaHybridBrain,
)


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


def test_gemma_component_is_silent_without_evidenced_impasse() -> None:
    policy = GemmaAugmentedSymbolicPolicy(
        MindConfig(enable_epistemic_state_graph=True),
        endpoint="http://127.0.0.1:1",
        model="test",
    )
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0), (0, 1)),
    )
    policy._last_observation = observation

    proposal = Decision(1, reason="symbolic-test")
    actual = policy._record(proposal)

    assert actual == proposal
    assert policy.gemma.metrics()["consultations"] == 0
    assert policy.gemma.last_event["consulted"] is False
