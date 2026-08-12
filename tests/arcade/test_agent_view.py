from __future__ import annotations

import pytest

from arcade.agent import (
    ARCADE_UI_VERSION,
    PAGE,
    resolve_model_choice,
    resolve_planner_choice,
)


def test_agent_arcade_mirrors_all_canonical_scratchpad_fields():
    assert ARCADE_UI_VERSION == "pretty-workspace-v20"
    assert "MODEL SCRATCHPAD · WORKSPACE MIRROR · UNVERIFIED" in PAGE
    assert "Waiting for the configured model." in PAGE
    assert "ACTION ALIASES · MODEL GLOSS, NOT CONTROL" in PAGE
    assert "R2 FEEDBACK · READ BY NEXT SEMANTIC MODEL" in PAGE
    assert '<select id=model-choice>' in PAGE
    assert '<select id=planner-choice>' in PAGE
    assert "model_choice:$('#model-choice').value" in PAGE
    assert "planner_choice:$('#planner-choice').value" in PAGE
    assert "model-context" not in PAGE
    for heading in ("Game Objective", "Explanation", "Goal", "Expectation", "Notes"):
        assert f"scratchField('{heading}'" in PAGE
    assert "const exact=s.model_scratchpad" in PAGE
    assert "QWEN SCRATCHPAD · UNVERIFIED" not in PAGE


def test_model_and_planner_pickers_share_game_row_and_playback_is_hidden():
    inline = '<label>GAME <select id=game></select></label><label>MODEL <select id=model-choice></select></label><label>PLANNER <select id=planner-choice></select></label>'
    assert inline in PAGE
    assert '<h2>PLAYBACK</h2>' not in PAGE
    assert '<select id=runs>' not in PAGE
    assert '<select id=runs hidden>' in PAGE
    assert '>LOAD</button>' not in PAGE


def test_agent_arcade_has_full_right_workspace_object_panel():
    assert 'class="panel workspace-column"' in PAGE
    assert 'id=workspace' in PAGE
    assert 'id=scratchpad-tab' not in PAGE
    assert 'id=workspace-tab' not in PAGE
    assert "DURABLE WORKSPACE OBJECT · MODEL WRITE" in PAGE
    assert "const workspace=data.workspace" in PAGE
    assert "ordered.map(name=>workspaceField(name,workspace[name]))" in PAGE
    assert "renderWithWorkspaceObject" in PAGE


def test_workspace_panel_pretty_prints_semantic_field_shapes():
    for marker in (
        "workspace-overview", "workspaceGoal", "workspaceComposition",
        "workspaceScratchpad", "workspaceAliases", "workspaceList",
        "RAW JSON", "preferred=['summary','objective_hypothesis'",
    ):
        assert marker in PAGE
    assert "Object.entries(workspace).map(([name,value])=>workspaceField" not in PAGE


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


def test_arcade_resolves_only_one_exact_server_allowlisted_planner():
    options = {
        "choices": [
            {"id": "deterministic", "selection": {"backend": "bounded-best-first-v0"}},
            {"id": "original", "selection": {"backend": "fallback-only-v0"}},
        ]
    }
    selected = resolve_planner_choice(options, "deterministic")
    selected["backend"] = "mutated"
    assert options["choices"][0]["selection"]["backend"] == "bounded-best-first-v0"
    for rejected in ("", None, "model-luna", {"backend": "original"}):
        with pytest.raises(ValueError, match="unknown planner choice"):
            resolve_planner_choice(options, rejected)
