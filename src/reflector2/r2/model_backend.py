"""Provider-neutral structured-model transport for R2.2.

The inherited controller still calls its semantic channel ``qwen`` in durable
ledger/event names.  This module treats that name as a compatibility alias:
model identity, transport, credentials, reasoning, and admission budgets are
resolved independently and never grant the model additional R2 authority.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from typing import Any, Callable, Mapping, MutableMapping


ENV_PREFIX = "R2_MODEL_"
SUPPORTED_PROVIDERS = frozenset({"openai", "openai-compatible"})
SUPPORTED_APIS = frozenset({"responses", "chat_completions"})
TRANSIENT_HTTP_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})
TOKEN_CACHE_LIMIT = 512
_TOKEN_CACHE: OrderedDict[str, int] = OrderedDict()
_TOKEN_CACHE_LOCK = threading.Lock()
_MODEL_ENV_LOCK = threading.Lock()
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})
_BROWSER_FIELDS = {
    "profile": f"{ENV_PREFIX}PROFILE",
    "model": f"{ENV_PREFIX}NAME",
    "context_window_tokens": f"{ENV_PREFIX}CONTEXT_WINDOW_TOKENS",
    "max_tokens": f"{ENV_PREFIX}MAX_TOKENS",
    "consolidation_max_tokens": f"{ENV_PREFIX}CONSOLIDATION_MAX_TOKENS",
    "frontier_token_budget": f"{ENV_PREFIX}FRONTIER_TOKEN_BUDGET",
    "reasoning_effort": f"{ENV_PREFIX}REASONING_EFFORT",
    "consolidation_reasoning_effort": f"{ENV_PREFIX}CONSOLIDATION_REASONING_EFFORT",
}


class ModelConfigurationError(ValueError):
    """A model profile is incomplete or internally inconsistent."""


class ModelTransportError(RuntimeError):
    """A model or exact-token-count request could not be completed."""


def add_cli_arguments(parser: Any) -> None:
    """Expose the same model selection surface to Arcade and Kaggle runners."""

    parser.add_argument("--model-profile")
    parser.add_argument("--model")
    parser.add_argument("--model-context-window-tokens", type=int)
    parser.add_argument("--model-max-tokens", type=int)
    parser.add_argument("--model-consolidation-max-tokens", type=int)
    parser.add_argument("--model-frontier-token-budget", type=int)
    parser.add_argument("--model-reasoning-effort")
    parser.add_argument("--model-consolidation-reasoning-effort")


def apply_cli_arguments(args: Any, *, environ: MutableMapping[str, str] | None = None) -> None:
    """Apply parsed flags as process-local overrides inherited by workers."""

    env = os.environ if environ is None else environ
    values = {
        f"{ENV_PREFIX}PROFILE": getattr(args, "model_profile", None),
        f"{ENV_PREFIX}NAME": getattr(args, "model", None),
        f"{ENV_PREFIX}CONTEXT_WINDOW_TOKENS": getattr(
            args, "model_context_window_tokens", None
        ),
        f"{ENV_PREFIX}MAX_TOKENS": getattr(args, "model_max_tokens", None),
        f"{ENV_PREFIX}CONSOLIDATION_MAX_TOKENS": getattr(
            args, "model_consolidation_max_tokens", None
        ),
        f"{ENV_PREFIX}FRONTIER_TOKEN_BUDGET": getattr(
            args, "model_frontier_token_budget", None
        ),
        f"{ENV_PREFIX}REASONING_EFFORT": getattr(
            args, "model_reasoning_effort", None
        ),
        f"{ENV_PREFIX}CONSOLIDATION_REASONING_EFFORT": getattr(
            args, "model_consolidation_reasoning_effort", None
        ),
    }
    for key, value in values.items():
        if value is not None:
            env[key] = str(value)


def _positive_integer(value: Any, label: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool):
        raise ModelConfigurationError(f"{label} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ModelConfigurationError(f"{label} must be an integer") from error
    minimum = 0 if allow_zero else 1
    if result < minimum:
        raise ModelConfigurationError(f"{label} must be >= {minimum}")
    return result


def _environment_override(
    target: MutableMapping[str, Any],
    environ: Mapping[str, str],
    env_name: str,
    key: str,
    *,
    integer: bool = False,
) -> bool:
    raw = environ.get(env_name)
    if raw is None or not raw.strip():
        return False
    target[key] = _positive_integer(raw, env_name) if integer else raw.strip()
    return True


def resolve_config(
    config: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve one immutable run configuration from a named model profile.

    Environment overrides are intentionally limited to non-secret metadata and
    budgets.  Only the *name* of an API-key variable enters this document; the
    credential itself is read at request time and can never enter a manifest.
    """

    env = os.environ if environ is None else environ
    output = copy.deepcopy(dict(config))
    legacy = copy.deepcopy(dict(output.get("qwen", {})))
    backend = output.get("model_backend")
    if not isinstance(backend, Mapping):
        raise ModelConfigurationError("model_backend configuration is required")
    profiles = backend.get("profiles")
    if not isinstance(profiles, Mapping) or not profiles:
        raise ModelConfigurationError("model_backend.profiles must be nonempty")
    profile_name = str(
        env.get(f"{ENV_PREFIX}PROFILE")
        or backend.get("active_profile")
        or ""
    ).strip()
    profile = profiles.get(profile_name)
    if not profile_name or not isinstance(profile, Mapping):
        raise ModelConfigurationError(f"unknown model profile: {profile_name!r}")

    resolved: dict[str, Any] = {**legacy, **copy.deepcopy(dict(profile))}
    resolved["profile"] = profile_name
    explicit_budget = {
        "context_window_tokens": _environment_override(
            resolved, env, f"{ENV_PREFIX}CONTEXT_WINDOW_TOKENS",
            "context_window_tokens", integer=True,
        ),
        "max_tokens": _environment_override(
            resolved, env, f"{ENV_PREFIX}MAX_TOKENS", "max_tokens", integer=True,
        ),
        "consolidation_max_tokens": _environment_override(
            resolved, env, f"{ENV_PREFIX}CONSOLIDATION_MAX_TOKENS",
            "consolidation_max_tokens", integer=True,
        ),
        "frontier_token_budget": _environment_override(
            resolved, env, f"{ENV_PREFIX}FRONTIER_TOKEN_BUDGET",
            "frontier_token_budget", integer=True,
        ),
    }
    _environment_override(resolved, env, f"{ENV_PREFIX}PROVIDER", "provider")
    _environment_override(resolved, env, f"{ENV_PREFIX}API", "api")
    _environment_override(resolved, env, f"{ENV_PREFIX}NAME", "model")
    # R2_MODEL is a concise alias useful in shell/Kaggle parameter sweeps.
    if not env.get(f"{ENV_PREFIX}NAME"):
        _environment_override(resolved, env, "R2_MODEL", "model")
    _environment_override(resolved, env, f"{ENV_PREFIX}ENDPOINT", "endpoint")
    _environment_override(
        resolved, env, f"{ENV_PREFIX}TOKEN_COUNT_ENDPOINT", "token_count_endpoint"
    )
    _environment_override(resolved, env, f"{ENV_PREFIX}API_KEY_ENV", "api_key_env")
    _environment_override(
        resolved, env, f"{ENV_PREFIX}REASONING_EFFORT", "reasoning_effort"
    )
    _environment_override(
        resolved, env, f"{ENV_PREFIX}CONSOLIDATION_REASONING_EFFORT",
        "consolidation_reasoning_effort",
    )
    _environment_override(
        resolved, env, f"{ENV_PREFIX}REQUEST_TIMEOUT_SECONDS",
        "request_timeout_seconds", integer=True,
    )
    _environment_override(
        resolved, env, f"{ENV_PREFIX}MAX_RETRIES", "max_retries", integer=True,
    )

    provider = str(resolved.get("provider") or "").strip().lower()
    api = str(resolved.get("api") or "").strip().lower()
    model = str(resolved.get("model") or "").strip()
    endpoint = str(resolved.get("endpoint") or "").strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ModelConfigurationError(f"unsupported model provider: {provider!r}")
    if api not in SUPPORTED_APIS:
        raise ModelConfigurationError(f"unsupported model API: {api!r}")
    if provider == "openai" and api != "responses":
        raise ModelConfigurationError("OpenAI profiles must use the Responses API")
    if not model:
        raise ModelConfigurationError("model profile must name a model")
    if not endpoint.startswith(("http://", "https://")):
        raise ModelConfigurationError("model endpoint must be an HTTP(S) URL")

    if bool(resolved.get("requires_explicit_budgets")):
        missing = [key for key, present in explicit_budget.items() if not present]
        if missing:
            rendered = ", ".join(f"{ENV_PREFIX}{key.upper()}" for key in missing)
            raise ModelConfigurationError(
                f"profile {profile_name!r} requires explicit budgets: {rendered}"
            )

    context = _positive_integer(
        resolved.get("context_window_tokens"), "context_window_tokens"
    )
    ordinary = _positive_integer(resolved.get("max_tokens"), "max_tokens")
    consolidation = _positive_integer(
        resolved.get("consolidation_max_tokens", ordinary),
        "consolidation_max_tokens",
    )
    reserve = max(
        ordinary,
        _positive_integer(
            resolved.get("reserved_tokens", ordinary), "reserved_tokens"
        ),
    )
    if max(ordinary, consolidation, reserve) >= context:
        raise ModelConfigurationError(
            "every output budget must be smaller than the context window"
        )
    # Admission reserves the actual request maximum; retaining this field also
    # keeps inherited result checks honest for ordinary turns.
    resolved.update({
        "provider": provider,
        "api": api,
        "model": model,
        "endpoint": endpoint,
        "context_window_tokens": context,
        "max_tokens": ordinary,
        "consolidation_max_tokens": consolidation,
        "reserved_tokens": reserve,
        "request_timeout_seconds": _positive_integer(
            resolved.get("request_timeout_seconds", 600),
            "request_timeout_seconds",
        ),
        "max_retries": _positive_integer(
            resolved.get("max_retries", 4), "max_retries", allow_zero=True
        ),
    })
    if api == "responses":
        count_endpoint = str(resolved.get("token_count_endpoint") or "").strip()
        if not count_endpoint.startswith(("http://", "https://")):
            raise ModelConfigurationError(
                "Responses profiles require an HTTP(S) token_count_endpoint"
            )
        resolved["token_count_endpoint"] = count_endpoint
        key_env = str(resolved.get("api_key_env") or "").strip()
        if not key_env:
            raise ModelConfigurationError("Responses profiles require api_key_env")
        resolved["api_key_env"] = key_env

    frontier_budget = resolved.get("frontier_token_budget")
    if frontier_budget is not None:
        frontier = _positive_integer(frontier_budget, "frontier_token_budget")
        if frontier + max(ordinary, consolidation) >= context:
            raise ModelConfigurationError(
                "frontier plus output reserve must be smaller than the context window"
            )
        resolved["frontier_token_budget"] = frontier
        active_control_profile = output.get("primary_profile")
        control_profiles = output.get("profiles")
        if (
            isinstance(active_control_profile, str)
            and isinstance(control_profiles, MutableMapping)
            and isinstance(control_profiles.get(active_control_profile), MutableMapping)
        ):
            control_profiles[active_control_profile]["frontier_token_budget"] = frontier

    # Canonical neutral key plus compatibility alias for inherited R2.2 code.
    output["model"] = copy.deepcopy(resolved)
    output["qwen"] = copy.deepcopy(resolved)
    return output


def require_credentials(config: Mapping[str, Any], *, environ: Mapping[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    key_name = config.get("api_key_env")
    if key_name and not str(env.get(str(key_name), "")).strip():
        raise ModelConfigurationError(
            f"{key_name} is required by model profile {config.get('profile')!r}"
        )


def public_metadata(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return reproducibility metadata with no credential values or paths."""

    keys = (
        "provider", "api", "profile", "model", "context_window_tokens",
        "reserved_tokens", "max_tokens", "consolidation_max_tokens",
        "reasoning_effort", "consolidation_reasoning_effort",
        "frontier_token_budget", "max_context_budget_rebuilds",
        "request_timeout_seconds", "max_retries",
    )
    return {key: config.get(key) for key in keys if config.get(key) is not None}


def browser_options(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the public, non-secret model surface exposed by Agent Arcade."""

    backend = config.get("model_backend")
    profiles = backend.get("profiles") if isinstance(backend, Mapping) else None
    if not isinstance(profiles, Mapping):
        raise ModelConfigurationError("model_backend.profiles must be nonempty")
    active = public_metadata(config.get("model", {}))
    public_profiles = []
    clean_env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(ENV_PREFIX) and key != "R2_MODEL"
    }
    for name, value in profiles.items():
        if not isinstance(name, str) or not isinstance(value, Mapping):
            continue
        descriptor = {
            "id": name,
            "provider": value.get("provider"),
            "api": value.get("api"),
            "requires_explicit_budgets": bool(value.get("requires_explicit_budgets")),
        }
        if not descriptor["requires_explicit_budgets"]:
            resolved = resolve_config(
                config, environ={**clean_env, f"{ENV_PREFIX}PROFILE": name}
            )
            descriptor["defaults"] = public_metadata(resolved["model"])
        public_profiles.append(descriptor)
    defaults_by_id = {
        item["id"]: item.get("defaults", {}) for item in public_profiles
    }
    qwen = defaults_by_id.get("local-qwen", active)
    luna = {**defaults_by_id.get("openai-gpt-5.6", {}), "model": "gpt-5.6-luna"}
    return {
        "active": active,
        "choices": [
            {
                "id": "qwen",
                "label": "Qwen (local)",
                "selection": {"profile": "local-qwen", "model": qwen.get("model", "")},
                "defaults": qwen,
            },
            {
                "id": "gpt-5.6-luna",
                "label": "GPT-5.6 Luna",
                "selection": {"profile": "openai-gpt-5.6", "model": "gpt-5.6-luna"},
                "defaults": luna,
            },
        ],
    }


def validate_browser_selection(
    config: Mapping[str, Any], selection: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate an Arcade selection and return public metadata plus env overrides."""

    if not isinstance(selection, Mapping):
        raise ModelConfigurationError("model selection must be an object")
    unknown = set(selection) - set(_BROWSER_FIELDS)
    if unknown:
        raise ModelConfigurationError(
            "unknown model selection fields: " + ", ".join(sorted(unknown))
        )
    backend = config.get("model_backend")
    profiles = backend.get("profiles") if isinstance(backend, Mapping) else None
    profile = str(selection.get("profile") or "").strip()
    if not isinstance(profiles, Mapping) or profile not in profiles:
        raise ModelConfigurationError(f"unknown model profile: {profile!r}")
    model = str(selection.get("model") or "").strip()
    if model and not _MODEL_NAME.fullmatch(model):
        raise ModelConfigurationError("model name contains unsupported characters")

    overrides = {f"{ENV_PREFIX}PROFILE": profile}
    if model:
        overrides[f"{ENV_PREFIX}NAME"] = model
    for field in (
        "context_window_tokens", "max_tokens", "consolidation_max_tokens",
        "frontier_token_budget",
    ):
        value = selection.get(field)
        if value not in (None, ""):
            number = _positive_integer(value, field)
            if number > 100_000_000:
                raise ModelConfigurationError(f"{field} is unreasonably large")
            overrides[_BROWSER_FIELDS[field]] = str(number)
    for field in ("reasoning_effort", "consolidation_reasoning_effort"):
        value = str(selection.get(field) or "").strip().lower()
        if value:
            if value not in _REASONING_EFFORTS:
                raise ModelConfigurationError(f"unsupported {field}: {value!r}")
            overrides[_BROWSER_FIELDS[field]] = value

    # The normal production resolver remains the single budget validator.
    resolved = resolve_config(config, environ={**os.environ, **overrides})
    return public_metadata(resolved["model"]), overrides


@contextmanager
def browser_model_environment(
    config: Mapping[str, Any], selection: Mapping[str, Any]
):
    """Apply one validated model choice for exactly one serialized Arcade run."""

    metadata, overrides = validate_browser_selection(config, selection)
    with _MODEL_ENV_LOCK:
        previous = {key: os.environ.get(key) for key in overrides}
        try:
            os.environ.update(overrides)
            yield metadata
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def _api_key(config: Mapping[str, Any], environ: Mapping[str, str]) -> str | None:
    key_name = config.get("api_key_env")
    if not key_name:
        return None
    value = str(environ.get(str(key_name), "")).strip()
    if not value:
        raise ModelConfigurationError(f"{key_name} is not set")
    return value


def _responses_content(content: Any) -> Any:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise ModelConfigurationError("message content must be text or a content list")
    converted: list[dict[str, Any]] = []
    for part in content:
        if not isinstance(part, Mapping):
            raise ModelConfigurationError("message content parts must be objects")
        kind = part.get("type")
        if kind in {"text", "input_text"}:
            converted.append({"type": "input_text", "text": str(part.get("text", ""))})
        elif kind in {"image_url", "input_image"}:
            raw_url = part.get("image_url")
            url = raw_url.get("url") if isinstance(raw_url, Mapping) else raw_url
            if not isinstance(url, str) or not url:
                raise ModelConfigurationError("image content requires image_url")
            converted.append({
                "type": "input_image",
                "image_url": url,
                "detail": str(part.get("detail") or "auto"),
            })
        else:
            raise ModelConfigurationError(f"unsupported message content type: {kind!r}")
    return converted


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    raise ModelConfigurationError(f"unsupported JSON Schema literal: {type(value).__name__}")


def _openai_schema(value: Any) -> Any:
    """Translate valid general JSON Schema into OpenAI's explicit-type subset."""

    if not isinstance(value, Mapping):
        return copy.deepcopy(value)
    # OpenAI Structured Outputs does not implement every general JSON Schema
    # keyword. R2's unchanged compiler still enforces omitted constraints after
    # parsing, so removing them here cannot grant authority to a model reply.
    schema = {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key not in {
            "uniqueItems", "minProperties", "maxProperties", "patternProperties",
            "propertyNames", "unevaluatedProperties", "contains", "minContains",
            "maxContains",
        }
    }
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        schema["properties"] = {
            str(name): _openai_schema(child) for name, child in properties.items()
        }
    for key in ("items", "additionalProperties", "not", "if", "then", "else"):
        if isinstance(schema.get(key), Mapping):
            schema[key] = _openai_schema(schema[key])
    for key in ("oneOf", "anyOf", "allOf", "prefixItems"):
        if isinstance(schema.get(key), list):
            schema[key] = [_openai_schema(child) for child in schema[key]]
    for key in ("$defs", "definitions", "dependentSchemas"):
        children = schema.get(key)
        if isinstance(children, Mapping):
            schema[key] = {
                str(name): _openai_schema(child) for name, child in children.items()
            }
    if "oneOf" in schema:
        if "anyOf" in schema:
            raise ModelConfigurationError("schema cannot combine oneOf and anyOf")
        schema["anyOf"] = schema.pop("oneOf")
    if "type" not in schema:
        if "const" in schema:
            schema["type"] = _json_type(schema["const"])
        elif isinstance(schema.get("enum"), list) and schema["enum"]:
            types = {_json_type(item) for item in schema["enum"]}
            if types <= {"integer", "number"}:
                schema["type"] = "number" if "number" in types else "integer"
            elif len(types) == 1:
                schema["type"] = next(iter(types))
        elif any(key in schema for key in ("properties", "required", "additionalProperties")):
            schema["type"] = "object"
        elif "items" in schema:
            schema["type"] = "array"
    if schema.get("type") == "object":
        properties = schema.get("properties")
        if properties is None:
            properties = {}
            schema["properties"] = properties
        if not isinstance(properties, Mapping):
            raise ModelConfigurationError("object schema properties must be an object")
        schema["required"] = list(properties)
        schema["additionalProperties"] = False
    return schema


def responses_payload(
    request_value: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    for_token_count: bool = False,
) -> dict[str, Any]:
    """Translate the legacy canonical chat envelope to Responses API input."""

    messages = request_value.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ModelConfigurationError("canonical model request requires messages")
    response_input = []
    for message in messages:
        if not isinstance(message, Mapping):
            raise ModelConfigurationError("messages must contain objects")
        role = str(message.get("role") or "").strip()
        if role not in {"user", "assistant", "system", "developer"}:
            raise ModelConfigurationError(f"unsupported Responses role: {role!r}")
        response_input.append({
            "role": role,
            "content": _responses_content(message.get("content")),
        })
    response_format = request_value.get("response_format")
    if not isinstance(response_format, Mapping):
        raise ModelConfigurationError("canonical model request requires response_format")
    container = response_format.get("json_schema")
    if response_format.get("type") != "json_schema" or not isinstance(container, Mapping):
        raise ModelConfigurationError("R2.2 requires a strict JSON-schema response")
    schema = container.get("schema")
    if not isinstance(schema, Mapping):
        raise ModelConfigurationError("response JSON schema is missing")
    payload: dict[str, Any] = {
        "model": str(config["model"]),
        "input": response_input,
        "text": {
            "format": {
                "type": "json_schema",
                "name": str(container.get("name") or "r2_semantic_response"),
                "strict": bool(container.get("strict", True)),
                "schema": _openai_schema(schema),
            }
        },
    }
    if not for_token_count:
        payload["max_output_tokens"] = _positive_integer(
            request_value.get("max_tokens"), "request.max_tokens"
        )
        payload["store"] = False
        effort = request_value.get("reasoning_effort", config.get("reasoning_effort"))
        if effort:
            payload["reasoning"] = {"effort": str(effort)}
    return payload


def _response_text(envelope: Mapping[str, Any]) -> str:
    direct = envelope.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    chunks: list[str] = []
    refusals: list[str] = []
    output = envelope.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, Mapping):
                    continue
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    chunks.append(str(part["text"]))
                elif part.get("type") == "refusal":
                    refusals.append(str(part.get("refusal") or "model refusal"))
    if chunks:
        return "".join(chunks)
    if refusals:
        raise ModelTransportError("; ".join(refusals))
    incomplete = envelope.get("incomplete_details")
    if incomplete:
        raise ModelTransportError(f"model response incomplete: {incomplete}")
    raise ModelTransportError("model response contained no output text")


def _normalized_usage(envelope: Mapping[str, Any]) -> dict[str, int]:
    usage = envelope.get("usage")
    if not isinstance(usage, Mapping):
        return {}
    prompt = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    completion = usage.get("output_tokens", usage.get("completion_tokens", 0))
    return {
        "prompt_tokens": int(prompt or 0),
        "completion_tokens": int(completion or 0),
        "total_tokens": int(usage.get("total_tokens") or int(prompt or 0) + int(completion or 0)),
    }


def _retry_delay(error: urllib.error.HTTPError, attempt: int, config: Mapping[str, Any]) -> float:
    retry_after = error.headers.get("Retry-After") if error.headers else None
    try:
        requested = float(retry_after) if retry_after is not None else 0.0
    except ValueError:
        requested = 0.0
    base = float(config.get("retry_base_seconds", 1.0))
    ceiling = float(config.get("retry_max_seconds", 20.0))
    return max(0.0, min(ceiling, max(requested, base * (2 ** attempt))))


def _post_json(
    endpoint: str,
    payload: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    timeout: float,
    environ: Mapping[str, str],
    opener: Callable[..., Any],
    sleeper: Callable[[float], None],
) -> tuple[str, dict[str, Any]]:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = _api_key(config, environ)
    if key is not None:
        headers["Authorization"] = f"Bearer {key}"
        # The stable canonical payload makes transient retry safe even when a
        # connection fails after the server accepted the first attempt.
        headers["Idempotency-Key"] = hashlib.sha256(encoded).hexdigest()
    retries = _positive_integer(
        config.get("max_retries", 4), "max_retries", allow_zero=True
    )
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            endpoint, data=encoded, headers=headers, method="POST"
        )
        try:
            with opener(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            envelope = json.loads(raw)
            if not isinstance(envelope, dict):
                raise ModelTransportError("model endpoint returned a non-object JSON envelope")
            return raw, envelope
        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            if error.code not in TRANSIENT_HTTP_STATUS or attempt >= retries:
                detail = body[:2000]
                raise ModelTransportError(
                    f"model endpoint HTTP {error.code}: {detail}"
                ) from error
            sleeper(_retry_delay(error, attempt, config))
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt >= retries:
                raise ModelTransportError(f"model endpoint unavailable: {error}") from error
            sleeper(min(float(config.get("retry_max_seconds", 20)), 2 ** attempt))
        except json.JSONDecodeError as error:
            raise ModelTransportError("model endpoint returned invalid JSON") from error
    raise AssertionError("retry loop exhausted without returning or raising")


def build_poster(
    config: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> Callable[[str, Any, float], dict[str, Any]]:
    """Build the FIFO poster without capturing or persisting an API key."""

    frozen = copy.deepcopy(dict(config))
    env = os.environ if environ is None else environ

    def post(endpoint: str, request_value: Any, timeout: float) -> dict[str, Any]:
        started = time.perf_counter()
        raw_body: str | None = None
        content: str | None = None
        parsed: Any = None
        transport_error: str | None = None
        normalized_usage: dict[str, int] = {}
        try:
            if not isinstance(request_value, Mapping):
                raise ModelConfigurationError("model request must be an object")
            wire = (
                responses_payload(request_value, frozen)
                if frozen["api"] == "responses"
                else copy.deepcopy(dict(request_value))
            )
            raw_body, envelope = _post_json(
                endpoint, wire, frozen, timeout=timeout, environ=env,
                opener=opener, sleeper=sleeper,
            )
            if frozen["api"] == "responses":
                content = _response_text(envelope)
            else:
                candidate = envelope["choices"][0]["message"]["content"]
                if not isinstance(candidate, str):
                    raise ModelTransportError("chat response content is not text")
                content = candidate
            parsed = json.loads(content)
            normalized_usage = _normalized_usage(envelope)
        except Exception as error:
            transport_error = f"{type(error).__name__}: {error}"
        return {
            "raw_body": raw_body,
            "content": content,
            "parsed": parsed,
            "latency_s": time.perf_counter() - started,
            "transport_error": transport_error,
            "normalized_usage": normalized_usage,
            "model_transport": {
                "provider": frozen["provider"],
                "api": frozen["api"],
                "profile": frozen["profile"],
                "model": frozen["model"],
            },
        }

    return post


def exact_openai_prompt_tokens(
    request_value: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    """Count the exact multimodal Responses input, with bounded caching."""

    env = os.environ if environ is None else environ
    payload = responses_payload(request_value, config, for_token_count=True)
    cache_key = json.dumps(
        {"endpoint": config["token_count_endpoint"], "payload": payload},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    with _TOKEN_CACHE_LOCK:
        cached = _TOKEN_CACHE.get(cache_key)
        if cached is not None:
            _TOKEN_CACHE.move_to_end(cache_key)
            return cached
    _raw, envelope = _post_json(
        str(config["token_count_endpoint"]), payload, config,
        timeout=float(config["request_timeout_seconds"]), environ=env,
        opener=opener, sleeper=sleeper,
    )
    count = _positive_integer(envelope.get("input_tokens"), "input_tokens", allow_zero=True)
    with _TOKEN_CACHE_LOCK:
        _TOKEN_CACHE[cache_key] = count
        _TOKEN_CACHE.move_to_end(cache_key)
        while len(_TOKEN_CACHE) > TOKEN_CACHE_LIMIT:
            _TOKEN_CACHE.popitem(last=False)
    return count


def install_token_counter(qc: Any) -> None:
    """Route admission through the serving model's exact counting boundary."""

    if getattr(qc, "_r2_model_backend_counter_installed", False):
        return
    original = qc.conservative_request_prompt_tokens

    def model_prompt_tokens(request: Mapping[str, Any], config: Mapping[str, Any]) -> int:
        if config.get("api") == "responses":
            return exact_openai_prompt_tokens(request, config)
        return original(request, config)

    qc.conservative_request_prompt_tokens = model_prompt_tokens
    qc._r2_model_backend_counter_installed = True
