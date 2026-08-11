from __future__ import annotations

import pytest

from arcade.agent import ARCADE_UI_VERSION, PAGE, resolve_model_choice


def test_agent_arcade_mirrors_all_canonical_scratchpad_fields():
    assert ARCADE_UI_VERSION == "canonical-r2-view-v16"
    assert "MODEL SCRATCHPAD · WORKSPACE MIRROR · UNVERIFIED" in PAGE
    assert "Waiting for the configured model." in PAGE
    assert "ACTION ALIASES · MODEL GLOSS, NOT CONTROL" in PAGE
    assert "R2 FEEDBACK · READ BY NEXT SEMANTIC MODEL" in PAGE
    assert '<select id=model-choice>' in PAGE
    assert "model_choice:$('#model-choice').value" in PAGE
    assert "model-context" not in PAGE
    for heading in ("Game Objective", "Explanation", "Goal", "Expectation", "Notes"):
        assert f"scratchField('{heading}'" in PAGE
    assert "const exact=s.model_scratchpad" in PAGE
    assert "QWEN SCRATCHPAD · UNVERIFIED" not in PAGE


def test_arcade_resolves_only_one_exact_server_allowlisted_choice():
    options = {
        "choices": [
            {"id": "qwen", "selection": {"profile": "local-qwen"}},
            {"id": "luna", "selection": {"profile": "openai", "model": "luna"}},
        ]
    }
    selected = resolve_model_choice(options, "luna")
    selected["model"] = "client-mutation"
    assert options["choices"][1]["selection"]["model"] == "luna"
    for rejected in ("", None, "terra", {"profile": "openai"}):
        with pytest.raises(ValueError, match="unknown model choice"):
            resolve_model_choice(options, rejected)
    duplicate = {"choices": [options["choices"][0], options["choices"][0]]}
    with pytest.raises(ValueError, match="unknown model choice"):
        resolve_model_choice(duplicate, "qwen")
