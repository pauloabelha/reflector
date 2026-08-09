from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("qwen_generic_explanation_priors", HERE / "experiment.py")
assert SPEC is not None and SPEC.loader is not None
EXPERIMENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPERIMENT
SPEC.loader.exec_module(EXPERIMENT)


def condition(predicate: str, left: str, right: str) -> dict[str, object]:
    return {"predicate": predicate, "arguments": [left, right]}


def hypothesis(
    conditions: list[dict[str, object]],
    *,
    operator: str = "Decrease",
    measure: str = "TranslationAlignmentResidual",
    effect: tuple[str, str] = ("?a", "?b"),
) -> dict[str, object]:
    return {
        "conditions": conditions,
        "preferred_consequence": {
            "operator": operator,
            "measure": measure,
            "arguments": list(effect),
        },
    }


def response(*hypotheses: dict[str, object]) -> dict[str, object]:
    return {
        "parsed": {
            "schema_version": "r2-relational-prior-v0",
            "hypotheses": list(hypotheses),
        }
    }


def compiled_template(raw: dict[str, object]) -> object:
    compilation = EXPERIMENT.compile_response(response(raw))
    assert compilation["valid_json_contract"] is True
    assert compilation["rejected"] == []
    templates = EXPERIMENT.templates_from_compilation(compilation)
    assert len(templates) == 1
    return templates[0]


def state_with(*facts: tuple[str, str, str]) -> dict[str, object]:
    return {
        "relations": [
            {"predicate": predicate, "arguments": [left, right]}
            for predicate, left, right in facts
        ]
    }


def test_alpha_equivalent_hypotheses_share_identity_and_are_deduplicated() -> None:
    original = hypothesis(
        [
            condition("SameOutline", "?a", "?b"),
            condition("SameOutline", "?a", "?c"),
            condition("SameInteriorLayout", "?a", "?b"),
            condition("DifferentInteriorLayout", "?a", "?c"),
        ]
    )
    renamed = hypothesis(
        [
            condition("SameOutline", "?d", "?c"),
            condition("SameOutline", "?d", "?a"),
            condition("SameInteriorLayout", "?d", "?c"),
            condition("DifferentInteriorLayout", "?d", "?a"),
        ],
        effect=("?d", "?c"),
    )

    original_compilation = EXPERIMENT.compile_response(response(original))
    renamed_compilation = EXPERIMENT.compile_response(response(renamed))
    together = EXPERIMENT.compile_response(response(original, renamed))

    assert original_compilation["accepted"][0]["canonical_hash"] == renamed_compilation["accepted"][0]["canonical_hash"]
    assert len(together["accepted"]) == 1
    assert [item["reason"] for item in together["rejected"]] == ["duplicate-template"]


def test_invalid_top_level_contract_is_not_accepted() -> None:
    compilation = EXPERIMENT.compile_response(
        {
            "parsed": {
                "schema_version": "r2-relational-prior-v0",
                "hypotheses": [],
                "explanation": "extra prose",
            }
        }
    )

    assert compilation == {
        "valid_json_contract": False,
        "accepted": [],
        "rejected": [{"reason": "top-level-contract"}],
    }


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (
            hypothesis([condition("SameShape", "?a", "?b")]),
            "unknown-predicate",
        ),
        (
            hypothesis(
                [condition("SameOutline", "?a", "?b")],
                measure="ContactResidual",
            ),
            "unsupported-consequence",
        ),
        (
            hypothesis(
                [condition("SameOutline", "?a", "?b")],
                operator="Preserve",
            ),
            "unsupported-consequence",
        ),
        (
            hypothesis(
                [condition("SameOutline", "?a", "?b")],
                effect=("?a", "?c"),
            ),
            "ungrounded-effect-variable",
        ),
    ],
)
def test_invalid_predicate_or_effect_is_rejected(raw: dict[str, object], reason: str) -> None:
    compilation = EXPERIMENT.compile_response(response(raw))

    assert compilation["valid_json_contract"] is True
    assert compilation["accepted"] == []
    assert [item["reason"] for item in compilation["rejected"]] == [reason]


def test_grounding_distinguishes_unique_ambiguous_and_unbound_effect_pairs() -> None:
    template = compiled_template(
        hypothesis(
            [
                condition("SameOutline", "?a", "?b"),
                condition("SameInteriorLayout", "?a", "?b"),
            ]
        )
    )
    unique = state_with(
        ("SameOutline", "f00", "f01"),
        ("SameInteriorLayout", "f00", "f01"),
    )
    ambiguous = state_with(
        ("SameOutline", "f00", "f01"),
        ("SameInteriorLayout", "f00", "f01"),
        ("SameOutline", "f02", "f03"),
        ("SameInteriorLayout", "f02", "f03"),
    )
    unbound = state_with(
        ("SameOutline", "f00", "f01"),
        ("DifferentInteriorLayout", "f00", "f01"),
    )

    unique_result = EXPERIMENT.ground_template(template, unique)
    ambiguous_result = EXPERIMENT.ground_template(template, ambiguous)
    unbound_result = EXPERIMENT.ground_template(template, unbound)

    assert unique_result["status"] == "bound"
    assert unique_result["effect_pair"] == ["f00", "f01"]
    assert unique_result["effect_pair_count"] == 1
    assert ambiguous_result["status"] == "ambiguous"
    assert ambiguous_result["effect_pair"] is None
    assert ambiguous_result["effect_pair_count"] == 2
    assert unbound_result["status"] == "unbound"
    assert unbound_result["effect_pair"] is None
    assert unbound_result["grounding_count"] == 0


def test_frozen_prompt_and_payload_do_not_leak_game_or_action_identity() -> None:
    prompt = (HERE / "PROMPT.txt").read_text(encoding="utf-8")
    selected = json.loads((HERE / "selected_games.json").read_text(encoding="utf-8"))
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    state = {
        "frame": {"height": 8, "width": 8},
        "opaque_legal_action_count": 7,
        "entities": [],
        "relations": [],
        "truncation": {"maximum_entities": 16, "entities_retained": 0},
    }
    payload = EXPERIMENT.qwen_payload(state, config)
    rendered = payload["messages"][0]["content"]
    lowered_prompt = prompt.lower()

    for game_id in selected["cohort"]:
        assert game_id.lower() not in lowered_prompt
        assert game_id.lower() not in rendered.lower()
    assert "arc-action" not in rendered.lower()
    assert "action_id" not in rendered.lower()
    assert "action_token" not in rendered.lower()
    assert re.search(r"\baction\s*[-:#]?\s*\d+\b", rendered.lower()) is None
    assert "opaque_legal_action_count" in rendered
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True
