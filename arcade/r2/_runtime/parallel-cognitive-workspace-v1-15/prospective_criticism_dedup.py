"""Packet-identity guard for v1.9 prospective evidence-return criticism.

Environment evidence is already durable before this boundary.  This adapter
filters only the selected prediction IDs passed to the criticism renderer: a
schema whose cumulative *probe* packet already has an immutable criticism is
not rendered again from a newer grounding state.  A changed packet receives a
new key and proceeds through the frozen v1.9 implementation unchanged.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


PROTOCOL = "prospective-criticism-packet-dedup-v1.15"


class ProspectiveCriticismDedupError(RuntimeError):
    """An existing criticism key does not describe its embedded packet."""


def criticism_key(
    stable_hash: Callable[[Any], str], schema_id: str, packet: Mapping[str, Any]
) -> str:
    """The exact identity formula frozen by v1.9."""

    return f"prospective-return:{schema_id}:{stable_hash(packet)}"


def _groups(
    bridge: Any, state: Any, selected_prediction_ids: Sequence[str]
) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for prediction_id in selected_prediction_ids:
        schema_id = bridge.prediction_schema_id(state, str(prediction_id))
        if schema_id is not None:
            output.setdefault(str(schema_id), []).append(str(prediction_id))
    return output


def _existing_packets(state: Any, status: str) -> dict[str, list[Any]]:
    output: dict[str, list[Any]] = {}
    for item in state.objects:
        if not (
            item.kind == "structured_criticism"
            and item.created_by == "r2"
            and item.payload.get("status") == status
            and isinstance(item.identity.get("criticism_key"), str)
        ):
            continue
        witness = item.payload.get("structured_witness")
        packet = witness.get("evidence_packet") if isinstance(witness, Mapping) else None
        output.setdefault(str(item.identity["criticism_key"]), []).append(packet)
    return output


def novel_packet_selection(
    bridge: Any,
    stable_hash: Callable[[Any], str],
    state: Any,
    selected_prediction_ids: Sequence[str],
) -> dict[str, Any]:
    """Classify schema groups solely by cumulative probe-packet identity."""

    groups = _groups(bridge, state, selected_prediction_ids)
    existing = _existing_packets(state, str(bridge.RETURN_STATUS))
    novel_schemas: list[str] = []
    reused_schemas: list[str] = []
    empty_schemas: list[str] = []
    keys: dict[str, str] = {}
    for schema_id in sorted(groups):
        packet = bridge.cumulative_evidence_packet(state, schema_id)
        if not packet.get("rows"):
            empty_schemas.append(schema_id)
            continue
        key = criticism_key(stable_hash, schema_id, packet)
        keys[schema_id] = key
        embedded = existing.get(key, ())
        if embedded and not any(value == packet for value in embedded):
            raise ProspectiveCriticismDedupError(
                "existing criticism key does not match embedded evidence packet"
            )
        if embedded:
            reused_schemas.append(schema_id)
        else:
            novel_schemas.append(schema_id)
    novel = set(novel_schemas)
    filtered = tuple(
        str(prediction_id)
        for prediction_id in selected_prediction_ids
        if bridge.prediction_schema_id(state, str(prediction_id)) in novel
    )
    return {
        "protocol": PROTOCOL,
        "selected_prediction_ids": filtered,
        "novel_schema_ids": tuple(novel_schemas),
        "reused_schema_ids": tuple(reused_schemas),
        "empty_schema_ids": tuple(empty_schemas),
        "criticism_keys": keys,
    }


def wrap_return_evidence_as_criticism(
    bridge: Any,
    stable_hash: Callable[[Any], str],
    fallback: Callable[..., Any],
) -> Callable[..., Any]:
    """Call frozen v1.9 only for schemas whose exact packet is novel."""

    def return_evidence_as_criticism(
        root: Any,
        workspace_id: str,
        state: Any,
        *,
        before_grid: Any,
        after_grid: Any,
        legal: Sequence[int],
        selected_prediction_ids: Sequence[str],
    ) -> Any:
        selection = novel_packet_selection(
            bridge, stable_hash, state, selected_prediction_ids
        )
        filtered = selection["selected_prediction_ids"]
        if not filtered:
            # The environment evidence was committed by the caller before this
            # boundary.  Returning state reuses the prior immutable criticism.
            return state
        return fallback(
            root,
            workspace_id,
            state,
            before_grid=before_grid,
            after_grid=after_grid,
            legal=legal,
            selected_prediction_ids=filtered,
        )

    return return_evidence_as_criticism


def install(
    owner: Any,
    *,
    bridge: Any,
    stable_hash: Callable[[Any], str],
) -> Any:
    """Patch the v1.9 module global resolved by its transition wrapper."""

    if getattr(owner, "_PROSPECTIVE_CRITICISM_DEDUP_V115_INSTALLED", False):
        return owner
    fallback = owner._return_evidence_as_criticism
    owner._PROSPECTIVE_CRITICISM_DEDUP_V115_BASE = fallback
    owner._return_evidence_as_criticism = wrap_return_evidence_as_criticism(
        bridge, stable_hash, fallback
    )
    owner._PROSPECTIVE_CRITICISM_DEDUP_V115_INSTALLED = True
    return owner


__all__ = [
    "PROTOCOL",
    "ProspectiveCriticismDedupError",
    "criticism_key",
    "install",
    "novel_packet_selection",
    "wrap_return_evidence_as_criticism",
]
