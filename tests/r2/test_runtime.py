from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from types import SimpleNamespace
import urllib.error

import pytest

from reflector2.r2 import model_backend as backend


def base_config() -> dict:
    return {
        "primary_profile": "control",
        "profiles": {"control": {"frontier_token_budget": 6400}},
        "qwen": {
            "endpoint": "http://127.0.0.1:8081/v1/chat/completions",
            "model": "local-model",
            "context_window_tokens": 16384,
            "reserved_tokens": 2048,
            "max_tokens": 2048,
            "consolidation_max_tokens": 5120,
            "request_timeout_seconds": 180,
        },
        "model_backend": {
            "active_profile": "local",
            "profiles": {
                "local": {
                    "provider": "openai-compatible",
                    "api": "chat_completions",
                    "max_retries": 0,
                },
                "openai-known": {
                    "provider": "openai",
                    "api": "responses",
                    "endpoint": "https://api.openai.com/v1/responses",
                    "token_count_endpoint": "https://api.openai.com/v1/responses/input_tokens",
                    "api_key_env": "OPENAI_API_KEY",
                    "model": "gpt-known",
                    "context_window_tokens": 100000,
                    "reserved_tokens": 4000,
                    "max_tokens": 4000,
                    "consolidation_max_tokens": 8000,
                    "frontier_token_budget": 12000,
                    "reasoning_effort": "medium",
                    "max_retries": 3,
                },
                "openai-custom": {
                    "provider": "openai",
                    "api": "responses",
                    "endpoint": "https://api.openai.com/v1/responses",
                    "token_count_endpoint": "https://api.openai.com/v1/responses/input_tokens",
                    "api_key_env": "OPENAI_API_KEY",
                    "model": "",
                    "requires_explicit_budgets": True,
                },
            },
        },
    }


def canonical_request() -> dict:
    return {
        "model": "legacy-name",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "inspect"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ],
        }],
        "temperature": 0,
        "seed": 1,
        "max_tokens": 321,
        "thinking_budget_tokens": 17,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "answer",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ok"],
                    "properties": {"ok": {"type": "boolean"}},
                },
            },
        },
    }


class Response:
    def __init__(self, value: dict):
        self.body = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def test_profile_resolution_is_model_neutral_and_never_materializes_key():
    resolved = backend.resolve_config(
        base_config(),
        environ={
            "R2_MODEL_PROFILE": "openai-known",
            "R2_MODEL_NAME": "gpt-another",
            "OPENAI_API_KEY": "secret-value",
        },
    )
    assert resolved["model"]["model"] == "gpt-another"
    assert resolved["qwen"] == resolved["model"]
    assert resolved["profiles"]["control"]["frontier_token_budget"] == 12000
    assert "secret-value" not in json.dumps(resolved)
    assert resolved["model"]["api_key_env"] == "OPENAI_API_KEY"


def test_unknown_model_requires_explicit_fail_closed_budgets():
    env = {"R2_MODEL_PROFILE": "openai-custom", "R2_MODEL_NAME": "future-model"}
    with pytest.raises(backend.ModelConfigurationError, match="requires explicit budgets"):
        backend.resolve_config(base_config(), environ=env)
    env.update({
        "R2_MODEL_CONTEXT_WINDOW_TOKENS": "200000",
        "R2_MODEL_MAX_TOKENS": "6000",
        "R2_MODEL_CONSOLIDATION_MAX_TOKENS": "12000",
        "R2_MODEL_FRONTIER_TOKEN_BUDGET": "20000",
    })
    resolved = backend.resolve_config(base_config(), environ=env)
    assert resolved["model"]["model"] == "future-model"
    assert resolved["model"]["context_window_tokens"] == 200000


def test_responses_translation_removes_local_dialect_and_preserves_schema_and_image():
    config = backend.resolve_config(
        base_config(), environ={"R2_MODEL_PROFILE": "openai-known"}
    )["model"]
    wire = backend.responses_payload(canonical_request(), config)
    assert wire["model"] == "gpt-known"
    assert wire["max_output_tokens"] == 321
    assert wire["reasoning"] == {"effort": "medium"}
    assert "temperature" not in wire and "seed" not in wire
    assert wire["input"][0]["content"][0] == {"type": "input_text", "text": "inspect"}
    assert wire["input"][0]["content"][1]["type"] == "input_image"
    assert wire["text"]["format"]["schema"]["required"] == ["ok"]
    assert wire["text"]["format"]["schema"]["type"] == "object"
    assert backend._openai_schema({"const": "r2"}) == {"const": "r2", "type": "string"}
    assert backend._openai_schema({"enum": [1, 2]})["type"] == "integer"
    narrowed = backend._openai_schema({
        "type": "object", "uniqueItems": True, "maxProperties": 3,
        "properties": {"x": {"const": 1}},
    })
    assert "uniqueItems" not in narrowed and "maxProperties" not in narrowed
    assert narrowed["properties"]["x"]["type"] == "integer"
    assert narrowed["required"] == ["x"]
    assert backend._openai_schema({"oneOf": [{"const": "x"}]}) == {
        "anyOf": [{"const": "x", "type": "string"}]
    }


def test_openai_poster_authenticates_normalizes_usage_and_parses_structured_output():
    config = backend.resolve_config(
        base_config(), environ={"R2_MODEL_PROFILE": "openai-known"}
    )["model"]
    seen = {}

    def opener(request, *, timeout):
        seen["timeout"] = timeout
        seen["authorization"] = request.headers.get("Authorization")
        seen["idempotency_key"] = request.get_header("Idempotency-key")
        seen["payload"] = json.loads(request.data)
        return Response({
            "status": "completed",
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": '{"ok":true}'}],
            }],
            "usage": {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15},
        })

    poster = backend.build_poster(
        config, environ={"OPENAI_API_KEY": "test-key"}, opener=opener
    )
    result = poster(config["endpoint"], canonical_request(), 42)
    assert result["transport_error"] is None
    assert result["parsed"] == {"ok": True}
    assert result["normalized_usage"] == {
        "prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15,
    }
    assert seen["authorization"] == "Bearer test-key"
    assert len(seen["idempotency_key"]) == 64
    assert seen["timeout"] == 42
    assert seen["payload"]["store"] is False


def test_exact_token_count_uses_server_multimodal_counter_and_cache():
    config = backend.resolve_config(
        base_config(),
        environ={"R2_MODEL_PROFILE": "openai-known", "R2_MODEL_NAME": "cache-unique"},
    )["model"]
    calls = []

    def opener(request, *, timeout):
        calls.append((request.full_url, json.loads(request.data), timeout))
        return Response({"input_tokens": 777})

    kwargs = {
        "environ": {"OPENAI_API_KEY": "test-key"},
        "opener": opener,
        "sleeper": lambda _delay: None,
    }
    assert backend.exact_openai_prompt_tokens(canonical_request(), config, **kwargs) == 777
    assert backend.exact_openai_prompt_tokens(canonical_request(), config, **kwargs) == 777
    assert len(calls) == 1
    assert calls[0][0].endswith("/responses/input_tokens")
    assert "max_output_tokens" not in calls[0][1]


def test_transient_http_error_retries_but_permanent_error_is_recorded():
    config = backend.resolve_config(
        base_config(), environ={"R2_MODEL_PROFILE": "openai-known"}
    )["model"]
    attempts = []
    delays = []

    def retrying(request, *, timeout):
        attempts.append(request)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(
                request.full_url, 429, "rate limited", {"Retry-After": "0"}, io.BytesIO(b"busy")
            )
        return Response({
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"ok":true}'}
            ]}],
            "usage": {},
        })

    result = backend.build_poster(
        config, environ={"OPENAI_API_KEY": "key"}, opener=retrying,
        sleeper=delays.append,
    )(config["endpoint"], canonical_request(), 5)
    assert result["transport_error"] is None
    assert len(attempts) == 2 and len(delays) == 1

    def permanent(request, *, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 400, "bad", {}, io.BytesIO(b"invalid model")
        )

    failed = backend.build_poster(
        config, environ={"OPENAI_API_KEY": "key"}, opener=permanent,
        sleeper=lambda _delay: None,
    )(config["endpoint"], canonical_request(), 5)
    assert "HTTP 400" in failed["transport_error"]


def test_shared_cli_surface_applies_worker_inherited_environment():
    parser = argparse.ArgumentParser()
    backend.add_cli_arguments(parser)
    args = parser.parse_args([
        "--model-profile", "openai-custom", "--model", "gpt-future",
        "--model-context-window-tokens", "123000",
        "--model-max-tokens", "5000",
        "--model-consolidation-max-tokens", "9000",
        "--model-frontier-token-budget", "15000",
    ])
    env = {}
    backend.apply_cli_arguments(args, environ=env)
    assert env["R2_MODEL_PROFILE"] == "openai-custom"
    assert env["R2_MODEL_NAME"] == "gpt-future"
    assert env["R2_MODEL_CONTEXT_WINDOW_TOKENS"] == "123000"


def test_r22_runtime_manifest_is_independent_of_experiments(monkeypatch):
    monkeypatch.delenv("R2_MODEL_PROFILE", raising=False)
    monkeypatch.delenv("R2_MODEL_NAME", raising=False)
    from reflector2.r2 import experiment

    config = experiment.load_config()
    manifest = experiment.build_manifest(config)
    assert manifest["experiment"] == "r2.2-agent-arcade"
    assert manifest["runtime_ownership"] == "reflector2.r2-canonical-runtime"
    assert manifest["semantic_model"]["profile"] == "local-qwen"
    assert manifest["sources"]
    assert all(not path.startswith("experiments/") for path in manifest["sources"])

    package = Path(experiment.__file__).resolve().parent
    for source in package.rglob("*.py"):
        assert 'REPO / "experiments"' not in source.read_text(encoding="utf-8")


def test_canonical_r2_owns_model_code_and_arcade_owns_only_the_view():
    root = Path(__file__).parents[2]
    package = root / "src/reflector2/r2"
    viewer = root / "arcade"
    assert (package / "model_backend.py").is_file()
    assert (package / "scratchpad.py").is_file()
    assert (package / "experiment.py").is_file()
    assert (viewer / "agent.py").is_file()
    assert not (viewer / "r2").exists()
    assert not any(viewer.glob("*model_backend*.py"))


def test_live_runtime_keeps_exact_workspace_separate_from_ui_traces():
    from reflector2.r2.runtime import LiveRuntime

    runtime = LiveRuntime()
    note = {
        "summary": "current model write",
        "model_scratchpad": {
            "game_objective": "finish",
            "explanation": "fit",
            "goal": "reduce the gap",
            "expectation": "gap decreases",
            "notes": "open",
        },
        "goal_proposals": [{"verb": "fit"}],
    }
    runtime.set_qwen_scratchpad(note)
    note["goal_proposals"][0]["verb"] = "mutated-after-publish"
    runtime.record_r2_action_trace("observed action")
    snapshot = runtime.read()

    assert snapshot["workspace"]["goal_proposals"] == [{"verb": "fit"}]
    assert "r2_action_traces" not in snapshot["workspace"]
    assert snapshot["scratchpad"]["r2_action_traces"] == ["observed action"]


def test_live_runtime_seeds_the_existing_semantic_projection_on_frame_zero():
    from reflector2.r2.runtime import LiveRuntime
    from reflector2.r2.scratchpad import reset_episode_context

    class Observer:
        def fit_frame(self, frame, *, turn=0):
            return {"turn": turn, "frame_digest": "frame-zero"}

        def semantic_affordance_frontier(self):
            return {
                "protocol": "r2-observation-affordance-frontier-v0",
                "authority": "observation-derived-attention-only",
                "observations": [],
            }

    reset_episode_context()
    runtime = LiveRuntime()
    runtime.set_schema_observer(Observer())
    runtime.update(frame=[[0, 1]], turn=0)
    projection = runtime.read()["r2_semantic_projection"]
    assert projection["frame_digest"] == "frame-zero"
    assert projection["affordance_frontier"]["observations"] == []
    assert "semantic_affordances" not in runtime.read()


def test_live_runtime_publishes_successor_and_settlement_atomically():
    from reflector2.r2.runtime import LiveRuntime

    class Observer:
        def fit_frame(self, frame, *, turn=0):
            return {"turn": turn, "frame_marker": frame[0][0]}

    runtime = LiveRuntime()
    runtime.set_schema_observer(Observer())
    runtime.snapshot.update({"frame": [[1]], "turn": 0, "settlement": None})
    successor = SimpleNamespace(
        frame=[[2]], levels_completed=0, win_levels=1,
    )
    controller = SimpleNamespace(settlements=[], fast_path=SimpleNamespace(document=lambda: {}))

    runtime.after_action(successor, controller)
    staged = runtime.read()
    assert staged["frame"] == [[1]]
    assert staged["turn"] == 0
    assert staged["settlement"] is None

    settlement = {"action": 3, "observation_changed": True, "outcome": "changed"}
    runtime.publish_action_settlement(settlement)
    published = runtime.read()
    assert published["frame"] == [[2]]
    assert published["turn"] == 1
    assert published["settlement"] == settlement
    assert published["r2_1_schema_stats"]["frame_marker"] == 2


def test_r22_openai_profile_changes_model_and_all_budget_dimensions(monkeypatch):
    from reflector2.r2 import experiment

    monkeypatch.setenv("R2_MODEL_PROFILE", "openai-gpt-5.6")
    monkeypatch.setenv("R2_MODEL_NAME", "gpt-5.6-terra")
    config = experiment.load_config()
    model = config["model"]
    assert model["provider"] == "openai"
    assert model["api"] == "responses"
    assert model["model"] == "gpt-5.6-terra"
    assert model["context_window_tokens"] == 1_050_000
    assert model["max_tokens"] == 8192
    assert model["consolidation_max_tokens"] == 16384
    assert model["reasoning_effort"] == "medium"
    assert model["consolidation_reasoning_effort"] == "high"
    assert config["profiles"][config["primary_profile"]]["frontier_token_budget"] == 12000


def test_model_scratchpad_is_one_exact_five_field_object():
    from reflector2.r2 import scratchpad

    source = {
        "game_objective": "  complete the arrangement  ",
        "notes": "  observed successor  ",
        "expectation": "residual decreases",
        "goal": "fit the compatible structures",
        "explanation": "the structures instantiate fit",
    }
    canonical = scratchpad.canonical_model_scratchpad(source)
    assert list(canonical) == [
        "game_objective", "explanation", "goal", "expectation", "notes",
    ]
    assert canonical["game_objective"] == "complete the arrangement"
    assert canonical["notes"] == "observed successor"
    canonical["goal"] = "changed copy"
    assert source["goal"] == "fit the compatible structures"


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {},
        {"explanation": "x", "goal": "g", "expectation": "e", "notes": "n"},
        {"game_objective": "o", "explanation": "x", "goal": "g", "expectation": "e", "notes": "n", "extra": "no"},
        {"game_objective": "o", "explanation": "x", "goal": "g", "expectation": "e", "notes": 3},
        {"game_objective": "o", "explanation": "x", "goal": " ", "expectation": "e", "notes": "n"},
    ],
)
def test_model_scratchpad_rejects_shape_drift(invalid):
    from reflector2.r2 import scratchpad

    with pytest.raises(ValueError, match="model scratchpad"):
        scratchpad.canonical_model_scratchpad(invalid)


def test_model_scratchpad_serialization_is_stable_and_wysiwyg():
    from reflector2.r2 import scratchpad

    first = {"game_objective": "o", "explanation": "x", "goal": "g", "expectation": "e", "notes": "n"}
    reordered = {"notes": "n", "goal": "g", "explanation": "x", "game_objective": "o", "expectation": "e"}
    assert scratchpad.model_scratchpad_text(first) == scratchpad.model_scratchpad_text(reordered)
    assert json.loads(scratchpad.model_scratchpad_text(first)) == first


@pytest.mark.parametrize(
    "leak",
    [
        "A contiguous dormant run exists",
        "inspect the delta codec",
        "the ordered lossless projection is the goal",
        "retain a lossy event summary",
        "use transport projection as evidence",
        "event compression explains the board",
    ],
)
def test_transport_metadata_cannot_become_scratchpad_semantics(leak):
    from reflector2.r2 import scratchpad

    assert scratchpad.has_transport_metadata_leak({"goal": leak})


def test_game_semantics_do_not_trigger_transport_metadata_guard():
    from reflector2.r2 import scratchpad

    assert not scratchpad.has_transport_metadata_leak({
        "game_objective": "complete a compatible arrangement",
        "explanation": "three figures preserve their outline",
        "goal": "align compatible figures",
        "expectation": "fit residual decreases",
        "notes": "the latest successor moved the target downward",
    })


def test_every_new_settlement_makes_scratchpad_revision_due_until_consumed():
    from reflector2.r2 import scratchpad

    qc = SimpleNamespace(stable_hash=lambda _value: "a" * 64)
    empty = SimpleNamespace(objects=[])
    scratchpad.reset_episode_context()
    assert not scratchpad.epistemic_scratchpad_revision_due(empty, "w", qc)
    scratchpad.record_r2_transition_observation(
        action=2, observation_changed=True, outcome="changed", trace="moved",
        settlement={"adjudication": "confirmed"},
    )
    assert scratchpad.epistemic_scratchpad_revision_due(empty, "w", qc)
    evidence_ref = scratchpad.current_transition_evidence_ref()
    consumed = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", created_revision=2,
        object_id="note", payload={
            "workspace_ref": "ws:" + "a" * 16,
            "transition_evidence_ref": evidence_ref,
        },
    )])
    assert not scratchpad.epistemic_scratchpad_revision_due(consumed, "w", qc)
    scratchpad.reset_episode_context()


def test_stale_scratchpad_basis_is_detected_against_latest_settlement():
    from reflector2.r2 import scratchpad

    scratchpad.reset_episode_context()
    assert scratchpad.scratchpad_basis_is_current(None)
    scratchpad.record_r2_transition_observation(
        action=1, observation_changed=False, outcome="unchanged", trace="stable",
        settlement={},
    )
    latest = scratchpad.current_transition_evidence_ref()
    assert latest and scratchpad.scratchpad_basis_is_current(latest)
    assert not scratchpad.scratchpad_basis_is_current(None)
    assert not scratchpad.scratchpad_basis_is_current("r2-transition:stale")
    scratchpad.reset_episode_context()


def test_frame_zero_null_transition_is_a_current_scratchpad_basis():
    from reflector2.r2 import scratchpad

    scratchpad.reset_episode_context()
    context = {"r2_transition_observation": None}
    transition = context.get("r2_transition_observation") or {}
    assert transition.get("evidence_ref") is None
    assert scratchpad.scratchpad_basis_is_current(None)


def test_production_config_enforces_a_tight_semantic_loop():
    config = json.loads((Path(__file__).parents[2] / "src/reflector2/r2/config.json").read_text())
    model = config["qwen"]
    assert model["trigger_on_new_action_evidence"] is True
    assert model["eager_semantic_integration"] is True
    assert model["nonblocking_semantic_integration"] is False
    assert model["logical_release_delay_actions"] == 0
    assert model["max_calls_per_episode"] >= config["action_budget"] + 1


def test_both_semantic_paths_receive_the_workspace_scratchpad_verbatim():
    from reflector2.r2 import scratchpad

    source = Path(scratchpad.__file__).read_text(encoding="utf-8")
    assert 'document["model_scratchpad"] = copy.deepcopy(stored_scratchpad)' in source
    assert '"allowed_vocabulary", "model_scratchpad",' in source
    assert '"model_scratchpad": dict(scratchpad)' in source
    assert '"game_objective", "explanation", "goal", "expectation", "notes"' in source
    assert "game_objective to the current inferred condition" in source
    assert '"required": ["protocol", "request_id", "scratchpad", "workspace_write"]' in source
    assert "notes to what was preserved, discarded, refuted, or left open" in source
    assert "explanation_consolidation_due" in source
    assert "transport-metadata-semantic-leak" in source
    assert "stale-epistemic-scratchpad-basis" in source
    assert 'vocabulary.pop("delta_codec", None)' in source


def test_evidenced_failure_has_a_focused_non_authoritative_revision_transport():
    from reflector2.r2 import controller, scratchpad

    source = Path(scratchpad.__file__).read_text(encoding="utf-8")
    controller_source = Path(controller.__file__).read_text(encoding="utf-8")
    prompt = scratchpad.SEMANTIC_REVISION_PROMPT.lower()
    update_prompt = scratchpad.SEMANTIC_UPDATE_PROMPT.lower()
    assert "focused repair turn" in prompt
    assert "r2 alone grounds roles" in prompt
    assert "return no goal proposal" in prompt
    assert "one observed transition" in update_prompt
    assert "r2 alone grounds roles" in update_prompt
    assert '"protocol": "focused-semantic-revision-v0"' in source
    assert '"supported-goal-plateau"' in source
    assert "_merge_supported_goal_proposals" in source
    assert '"semantic_view": "focused-failure-repair"' in source
    assert "if post_action_update" in source
    assert '"abductive_compositions": "empty"' in source
    assert '"action_aliases": "empty"' in source
    assert '"cited_ids": "empty"' in source
    assert "post-action-null-history-claim" in source
    assert "evidence-failed-goal-proposal-retired" in source
    assert "control_goal_proposals" in controller_source
    assert '"roles": {"const": list(CONTROL_GOAL_ROLES)}' in source
    assert '"arguments": {"const": list(CONTROL_GOAL_ROLES)}' in source
    assert '"modality": {"enum": list(GENERATED_ROLE_MODALITIES)}' in source
    assert "independent learned aliases" in source
    assert 'properties["goal_proposals"]' in source
    assert '"minItems": 0, "maxItems": 2' in source


def test_arcade_picker_validates_custom_budgets_and_restores_environment(monkeypatch):
    monkeypatch.setenv("R2_MODEL_PROFILE", "local")
    selection = {
        "profile": "openai-custom",
        "model": "gpt-future.1",
        "context_window_tokens": 200000,
        "max_tokens": 5000,
        "consolidation_max_tokens": 9000,
        "frontier_token_budget": 15000,
        "reasoning_effort": "high",
        "consolidation_reasoning_effort": "xhigh",
    }
    metadata, overrides = backend.validate_browser_selection(base_config(), selection)
    assert metadata["model"] == "gpt-future.1"
    assert metadata["frontier_token_budget"] == 15000
    assert overrides["R2_MODEL_NAME"] == "gpt-future.1"
    with backend.browser_model_environment(base_config(), selection):
        assert backend.resolve_config(base_config())["model"]["model"] == "gpt-future.1"
    assert backend.resolve_config(base_config())["model"]["profile"] == "local"

    with pytest.raises(backend.ModelConfigurationError, match="requires explicit budgets"):
        backend.validate_browser_selection(
            base_config(), {"profile": "openai-custom", "model": "gpt-future.1"}
        )
    with pytest.raises(backend.ModelConfigurationError, match="unknown model selection"):
        backend.validate_browser_selection(
            base_config(), {**selection, "endpoint": "https://evil.invalid"}
        )


def test_arcade_picker_options_are_public_and_profile_budgeted():
    from reflector2.r2 import experiment

    options = backend.browser_options(experiment.load_config())
    assert [(item["id"], item["label"]) for item in options["choices"]] == [
        ("qwen", "Qwen (local)"),
        ("gpt-5.6-luna", "GPT-5.6 Luna"),
    ]
    luna = options["choices"][1]
    assert luna["selection"] == {
        "profile": "openai-gpt-5.6", "model": "gpt-5.6-luna"
    }
    assert luna["defaults"]["context_window_tokens"] == 1_050_000
    assert luna["defaults"]["consolidation_max_tokens"] == 16384
    assert "profiles" not in options and "suggested_models" not in options
    assert "api_key_env" not in json.dumps(options)
    assert "endpoint" not in json.dumps(options)


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        (None, "null"), (False, "boolean"), (3, "integer"), (3.5, "number"),
        ("x", "string"), ([], "array"), ({}, "object"),
    ],
)
def test_openai_schema_infers_every_json_literal_type(literal, expected):
    assert backend._openai_schema({"const": literal})["type"] == expected


def test_openai_schema_normalization_is_recursive_strict_and_non_mutating():
    source = {
        "type": "object",
        "required": ["stale", "optional"],
        "properties": {
            "protocol": {"const": "r2"},
            "items": {
                "type": "array", "uniqueItems": True,
                "items": {
                    "oneOf": [
                        {"type": "object", "maxProperties": 1,
                         "properties": {"n": {"enum": [1, 2]}}},
                        {"const": None},
                    ]
                },
            },
        },
    }
    original = json.loads(json.dumps(source))
    wire = backend._openai_schema(source)
    assert source == original
    assert wire["required"] == ["protocol", "items"]
    assert wire["additionalProperties"] is False
    assert wire["properties"]["protocol"]["type"] == "string"
    item = wire["properties"]["items"]["items"]
    assert "oneOf" not in item and len(item["anyOf"]) == 2
    assert item["anyOf"][0]["required"] == ["n"]
    assert item["anyOf"][0]["properties"]["n"]["type"] == "integer"
    assert "uniqueItems" not in wire["properties"]["items"]
    assert "maxProperties" not in item["anyOf"][0]


@pytest.mark.parametrize(
    "keyword",
    [
        "uniqueItems", "minProperties", "maxProperties", "patternProperties",
        "propertyNames", "unevaluatedProperties", "contains", "minContains",
        "maxContains",
    ],
)
def test_openai_schema_removes_unsupported_keywords_at_any_depth(keyword):
    source = {
        "type": "object",
        "properties": {"nested": {"type": "array", keyword: {} if keyword == "contains" else 1}},
    }
    assert keyword not in json.dumps(backend._openai_schema(source))


def test_openai_schema_rejects_ambiguous_or_malformed_constructs():
    with pytest.raises(backend.ModelConfigurationError, match="combine oneOf and anyOf"):
        backend._openai_schema({"oneOf": [], "anyOf": []})
    with pytest.raises(backend.ModelConfigurationError, match="properties must be an object"):
        backend._openai_schema({"type": "object", "properties": []})
    with pytest.raises(backend.ModelConfigurationError, match="unsupported JSON Schema literal"):
        backend._openai_schema({"const": object()})


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"profile": "missing"}, "unknown model profile"),
        ({"model": "bad model/name"}, "unsupported characters"),
        ({"reasoning_effort": "ultra"}, "unsupported reasoning_effort"),
        ({"max_tokens": 0}, "must be >= 1"),
        ({"max_tokens": 100_000_001}, "unreasonably large"),
        ({"unexpected": "x"}, "unknown model selection fields"),
    ],
)
def test_browser_selection_rejects_every_untrusted_dimension(change, message):
    selection = {"profile": "openai-known", "model": "gpt-known", **change}
    with pytest.raises(backend.ModelConfigurationError, match=message):
        backend.validate_browser_selection(base_config(), selection)


def test_browser_model_environment_restores_all_values_even_on_exception(monkeypatch):
    monkeypatch.setenv("R2_MODEL_PROFILE", "local")
    monkeypatch.setenv("R2_MODEL_NAME", "before")
    selection = {"profile": "openai-known", "model": "gpt-known"}
    with pytest.raises(RuntimeError, match="abort"):
        with backend.browser_model_environment(base_config(), selection):
            assert backend.resolve_config(base_config())["model"]["profile"] == "openai-known"
            raise RuntimeError("abort")
    assert backend.os.environ["R2_MODEL_PROFILE"] == "local"
    assert backend.os.environ["R2_MODEL_NAME"] == "before"


def test_kaggle_freezes_and_loads_the_same_production_runtime(monkeypatch):
    monkeypatch.delenv("R2_MODEL_PROFILE", raising=False)
    from reflector2.r2 import experiment, kaggle

    sources = kaggle.r2_source_hashes()
    assert "R2_2.md" in sources
    assert "src/reflector2/r2/experiment.py" in sources
    assert "src/reflector2/r2/model_backend.py" in sources
    assert any("parallel-generative-schema-fitting-v0/schema_engine.py" in path for path in sources)
    assert all(not path.startswith("experiments/") for path in sources)
    loaded = kaggle.load_r2()
    assert Path(loaded.__file__).resolve() == Path(experiment.__file__).resolve()
    assert loaded.load_config()["experiment"] == "r2.2-agent-arcade"
