"""Bounded visual semantic worker for native Reflector-II shared cognition."""

from __future__ import annotations

import base64
import json
import re
import struct
import urllib.request
import zlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .epistemic_workspace import EpistemicFrontier, canonical_json, content_hash
from .perception import Grid
from .shared_cognition import (
    GroundedProposal,
    NativeSharedCognition,
    SemanticSchemaProposal,
    SharedCognitionError,
)
from .store import SourceAtom, canonical_variable_ordinals


PROTOCOL = "native-r2-qwen-v1"
FORBIDDEN_PROMPT_KEYS = frozenset({"game", "game_id", "action", "action_id"})
MAX_CONDITIONS = 4
EXECUTABLE_MEASURES = (
    "TranslationAlignmentResidual",
    "OutsideCount",
    "OverlapDeficit",
    "TopologyMismatchCount",
    "RelationalResidual",
)
_ARC_CONTEXT = re.compile(
    r"arc:[^:]+:episode:[0-9]+:observation:[0-9]+:support:[0-9]+"
)
_ARC_ACTION = re.compile(r"arc-action:([0-9]+)")


class QwenWorkerError(ValueError):
    """A semantic-worker request or response violates the cognitive contract."""


@dataclass(frozen=True, slots=True)
class QwenOrientation:
    cursor: int = -1
    turn_index: int = 0


@dataclass(frozen=True, slots=True)
class QwenTurn:
    request_id: str
    basis_revision: int
    frontier: EpistemicFrontier
    document: dict[str, Any]
    request: dict[str, Any]
    visible_object_ids: frozenset[str]
    alias_to_object_id: Mapping[str, str]
    next_orientation: QwenOrientation


@dataclass(frozen=True, slots=True)
class QwenCompilation:
    valid: bool
    abstained: bool
    proposal: SemanticSchemaProposal | None
    revises_id: str | None
    criticism_id: str | None
    response_id: str
    rejection: str | None = None


@dataclass(frozen=True, slots=True)
class QwenIntegration:
    compilation: QwenCompilation
    grounded: GroundedProposal | None
    orientation: QwenOrientation


Poster = Callable[[str, Mapping[str, Any], float], Mapping[str, Any]]


_ARC_PALETTE = (
    (0, 0, 0),
    (0, 116, 217),
    (255, 65, 54),
    (46, 204, 64),
    (255, 220, 0),
    (170, 170, 170),
    (240, 18, 190),
    (255, 133, 27),
    (127, 219, 255),
    (135, 12, 37),
)


def _visual_color(value: int) -> tuple[int, int, int]:
    if 0 <= value < len(_ARC_PALETTE):
        return _ARC_PALETTE[value]
    digest = bytes.fromhex(content_hash({"visual-channel": value}))
    # Keep extension colors visible on black while remaining stable across
    # processes, machines, games, and turns.
    return tuple(48 + channel % 192 for channel in digest[:3])  # type: ignore[return-value]


def _png_chunk(kind: bytes, body: bytes) -> bytes:
    return (
        struct.pack(">I", len(body))
        + kind
        + body
        + struct.pack(">I", zlib.crc32(kind + body))
    )


def grid_png_data_url(grid: Grid, *, scale: int = 8) -> str:
    """Encode an exact integer grid as a nearest-neighbor RGB PNG."""

    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise QwenWorkerError("visual frame must be a non-empty rectangle")
    if not 1 <= scale <= 16:
        raise QwenWorkerError("visual scale must be in [1, 16]")
    rows: list[bytes] = []
    for row in grid:
        pixels = bytearray()
        for value in row:
            pixels.extend(_visual_color(int(value)) * scale)
        expanded = bytes(pixels)
        rows.extend(b"\x00" + expanded for _ in range(scale))
    width = len(grid[0]) * scale
    height = len(grid) * scale
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        signature
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(b"".join(rows), level=9))
        + _png_chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _forbidden(value: object, *, path: tuple[str, ...] = ()) -> str | None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key).lower()
            if key in FORBIDDEN_PROMPT_KEYS:
                return ".".join((*path, key))
            found = _forbidden(item, path=(*path, key))
            if found:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            found = _forbidden(item, path=(*path, str(index)))
            if found:
                return found
    elif isinstance(value, str):
        lowered = value.lower()
        if "arc-action:" in lowered or "game:" in lowered or _ARC_CONTEXT.search(value):
            return ".".join(path)
    return None


def _cognitive_projection(value: object) -> object:
    """Remove transport routing identity while preserving stable references."""

    if isinstance(value, Mapping):
        return {str(key): _cognitive_projection(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_cognitive_projection(item) for item in value]
    if isinstance(value, str):
        projected = _ARC_CONTEXT.sub(
            lambda match: "obs:" + content_hash(match.group(0))[:16], value
        )
        return _ARC_ACTION.sub(
            lambda match: "im:"
            + content_hash({"opaque_channel": int(match.group(1))})[:24],
            projected,
        )
    return value


def _response_schema(
    *,
    basis_aliases: Sequence[str],
    predicates: Sequence[str],
    revision_target_alias: str | None,
    criticism_alias: str | None,
) -> dict[str, Any]:
    # Grammar-level repetition of a dynamic visible-ID enum is surprisingly
    # expensive (the same 67-byte IDs occur in several branches).  Stable-ID
    # shape is constrained here and exact visible membership is enforced by
    # ``compile_response`` against the immutable turn sidecar.
    id_schema: dict[str, Any] = {
        "type": "string",
        "pattern": "^o[0-9]+$",
    }
    atom = {
        "type": "object",
        "additionalProperties": False,
        "required": ["predicate", "arguments"],
        "properties": {
            "predicate": {"type": "string", "enum": list(predicates)},
            "arguments": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "string",
                    "pattern": "^\\?[A-Za-z][A-Za-z0-9_]*$",
                },
            },
        },
    }
    proposal = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "name",
            "conditions",
            "operator",
            "measure",
            "effect_arguments",
            "basis_ids",
            "revises_id",
            "criticism_id",
        ],
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 80},
            "conditions": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_CONDITIONS,
                "items": atom,
            },
            "operator": {"type": "string", "enum": ["Decrease", "Increase"]},
            "measure": {"type": "string", "enum": list(EXECUTABLE_MEASURES)},
            "effect_arguments": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {
                    "type": "string",
                    "pattern": "^\\?[A-Za-z][A-Za-z0-9_]*$",
                },
            },
            "basis_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "uniqueItems": True,
                "items": {"type": "string", "enum": list(basis_aliases)},
            },
            "revises_id": (
                {"type": "null"}
                if revision_target_alias is None
                else {"type": "string", "const": revision_target_alias}
            ),
            "criticism_id": (
                {"type": "null"}
                if criticism_alias is None
                else {"type": "string", "const": criticism_alias}
            ),
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "native_r2_semantic_write",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["protocol", "request_id", "proposal", "abstain"],
                "properties": {
                    "protocol": {"type": "string", "const": PROTOCOL},
                    "request_id": {"type": "string"},
                    "proposal": {"anyOf": [{"type": "null"}, proposal]},
                    "abstain": {"type": "boolean"},
                },
            },
        },
    }


class QwenSemanticWorker:
    """Stateful, bounded renderer/compiler for a resident Qwen endpoint."""

    def __init__(
        self,
        *,
        endpoint: str = "http://127.0.0.1:8081/v1/chat/completions",
        model: str = "qwen3-vl-4b-thinking-q4_k_m",
        token_budget: int = 6400,
        root_limit: int = 24,
        max_deltas: int = 96,
        max_tokens: int = 2048,
        thinking_budget_tokens: int = 1024,
        timeout_seconds: float = 180.0,
        poster: Poster | None = None,
    ) -> None:
        if token_budget <= 0 or root_limit < 0 or max_deltas <= 0:
            raise QwenWorkerError("worker bounds must be positive")
        self.endpoint = endpoint
        self.model = model
        self.token_budget = token_budget
        self.root_limit = root_limit
        self.max_deltas = max_deltas
        self.max_tokens = max_tokens
        self.thinking_budget_tokens = thinking_budget_tokens
        self.timeout_seconds = timeout_seconds
        self.poster = poster or self._post

    @staticmethod
    def _post(
        endpoint: str, payload: Mapping[str, Any], timeout: float
    ) -> Mapping[str, Any]:
        request = urllib.request.Request(
            endpoint,
            data=canonical_json(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            parsed = json.loads(response.read())
        if not isinstance(parsed, Mapping):
            raise QwenWorkerError("completion endpoint returned a non-object")
        return parsed

    @staticmethod
    def _object_document(
        cognition: NativeSharedCognition,
        object_id: str,
        alias_by_id: Mapping[str, str],
    ) -> dict[str, Any]:
        item = cognition.epistemic.object(object_id)
        return {
            "id": alias_by_id[item.object_id],
            "kind": item.kind,
            "creator": item.creator,
            "revision": item.created_revision,
            "payload": _cognitive_projection(item.payload),
            "dependencies": [alias_by_id[value] for value in item.dependency_ids],
            "support": cognition.epistemic.support(item.object_id),
        }

    @staticmethod
    def _workspace_index(cognition: NativeSharedCognition) -> dict[str, Any]:
        """Return a compact exact-identity/topology index for bootstrap.

        Full canonical payloads remain in the authoritative hash-chained
        workspace.  Qwen gets their stable addresses, kinds, provenance,
        dependency topology, revisions, and payload digests; semantic payloads
        for the active dependency-closed cut are rendered in full separately.
        """

        objects = cognition.epistemic.objects
        ordinal = {item.object_id: index for index, item in enumerate(objects)}
        previous_revision = 0
        revision_deltas: list[int] = []
        for item in objects:
            revision_deltas.append(item.created_revision - previous_revision)
            previous_revision = item.created_revision
        return {
            "fidelity": "exact-addressable-index; canonical-payloads-external",
            "alias_scheme": "o<zero-based-created-order>",
            "object_count": len(objects),
            "canonical_id_manifest_digest": content_hash(
                [item.object_id for item in objects]
            ),
            "kinds": [item.kind for item in objects],
            "creators": [item.creator for item in objects],
            "created_revision_deltas": revision_deltas,
            "dependency_ordinals": [
                [ordinal[dependency] for dependency in item.dependency_ids]
                for item in objects
            ],
            "semantic_key_digests": [
                content_hash(item.semantic_key)[:16] for item in objects
            ],
            "payload_digests": [content_hash(item.payload)[:16] for item in objects],
        }

    def build_turn(
        self,
        cognition: NativeSharedCognition,
        *,
        orientation: QwenOrientation,
        request_id: str,
        current_frame: Grid,
        previous_frame: Grid | None = None,
        transition: Mapping[str, Any] | None = None,
    ) -> QwenTurn:
        frontier = cognition.epistemic.frontier(
            worker="qwen", budget=self.token_budget, root_limit=self.root_limit
        )
        alias_by_id = {
            item.object_id: f"o{index}"
            for index, item in enumerate(cognition.epistemic.objects)
        }
        alias_to_id = {alias: object_id for object_id, alias in alias_by_id.items()}
        frontier_values = [
            cognition.epistemic.object(object_id) for object_id in frontier.object_ids
        ]
        eligible_basis_ids = [
            item.object_id
            for item in frontier_values
            if item.kind
            in {"observation", "environment-evidence", "structured-criticism"}
        ]
        observed_predicates = sorted(
            {
                str(fact[0])
                for item in frontier_values
                if item.kind == "observation"
                for fact in item.payload.get("facts", ())
                if isinstance(fact, list) and len(fact) == 2
            }
        )
        if not eligible_basis_ids or not observed_predicates:
            raise QwenWorkerError(
                "active frontier lacks an observation basis or predicate vocabulary"
            )
        criticisms = [
            item for item in frontier_values if item.kind == "structured-criticism"
        ]
        criticism = max(criticisms, key=lambda item: item.created_revision, default=None)
        revision_target_id: str | None = None
        if criticism is not None:
            candidate = criticism.payload.get("target")
            if (
                isinstance(candidate, str)
                and candidate in alias_by_id
                and cognition.epistemic.object(candidate).kind == "semantic-schema"
            ):
                revision_target_id = candidate
            elif isinstance(candidate, str) and candidate in alias_by_id:
                target = cognition.epistemic.object(candidate)
                revision_target_id = next(
                    (
                        dependency
                        for dependency in target.dependency_ids
                        if cognition.epistemic.object(dependency).kind
                        == "semantic-schema"
                    ),
                    None,
                )
            else:
                criticism = None
            if revision_target_id is None:
                criticism = None
        deltas = cognition.epistemic.deltas(orientation.cursor)
        causal_ids = set(frontier.object_ids)
        if orientation.cursor == -1:
            # Bootstrap materializes the current cut and the complete compact
            # object/topology index.  Replaying all construction events here
            # would duplicate that state without adding cognition.
            delta_document = {
                "fidelity": "bootstrap-state-materialized; no-duplicate-events",
                "covered_revision": cognition.epistemic.revision,
                "event_count": len(deltas),
                "ordered_event_digest": content_hash(
                    [event.document() for event in deltas]
                ),
                "authoritative_index": self._workspace_index(cognition),
            }
        elif len(deltas) > self.max_deltas:
            exact = [
                _cognitive_projection(event.document())
                for event in deltas
                if event.event_id in causal_ids
                or any(object_id in event.body_json for object_id in causal_ids)
            ]
            delta_document: dict[str, Any] = {
                "fidelity": "small-lossy-dormant-run",
                "total_count": len(deltas),
                "ordered_run_digest": content_hash(
                    [event.document() for event in deltas]
                ),
                "exact_causal_events": exact[-self.max_deltas :],
            }
        else:
            delta_document = {
                "fidelity": "exact-ordered",
                "events": [
                    _cognitive_projection(event.document()) for event in deltas
                ],
            }
        document = {
            "protocol": PROTOCOL,
            "request_id": request_id,
            "basis_revision": cognition.epistemic.revision,
            "orientation": {
                "turn_index": orientation.turn_index,
                "cursor": orientation.cursor,
            },
            "workspace": {
                "frontier": [
                    self._object_document(cognition, object_id, alias_by_id)
                    for object_id in frontier.object_ids
                ],
                "mandatory_ids": [
                    alias_by_id[object_id] for object_id in frontier.mandatory_ids
                ],
                "omitted_root_count": len(frontier.omitted_root_ids),
            },
            "deltas": delta_document,
            "transition": None if transition is None else dict(transition),
            "revision_task": (
                None
                if criticism is None or revision_target_id is None
                else {
                    "target": alias_by_id[revision_target_id],
                    "criticism": alias_by_id[criticism.object_id],
                    "status": criticism.payload.get("status"),
                }
            ),
        }
        forbidden = _forbidden(document)
        if forbidden:
            raise QwenWorkerError(
                f"epistemic projection leaks forbidden transport identity at {forbidden}"
            )
        contract = (
            "You are Qwen, the semantic worker inside one shared Reflector-II epistemic world. "
            "The images are direct environment observations; workspace objects are addressable claims, not reality. "
            "Propose relational conditions that R2 can ground in the current observation. Use variables beginning with ?. "
            "If structured criticism or environment evidence is visible, revise its exact semantic target rather than repeating it. "
            "Cite visible observation/relation/evidence IDs. You may increase attention by proposing, but you cannot assert support. "
            "Only emit a Decrease/Increase consequence over a named measure and exactly two effect variables. "
            "Condition arguments must be abstract variables such as ?a and ?b, never situated object names. "
            "The two effect variables must occur in the conditions. When revision_task is null, revises_id and criticism_id must be null. "
            "Abstain when the visible evidence cannot justify a mechanically groundable proposal."
        )
        content: list[dict[str, Any]] = [{"type": "text", "text": contract}]
        if previous_frame is not None:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": grid_png_data_url(previous_frame)},
                }
            )
            content.append(
                {"type": "text", "text": "Immediately preceding visual frame."}
            )
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": grid_png_data_url(current_frame)},
            }
        )
        content.append({"type": "text", "text": "Current visual frame."})
        content.append(
            {"type": "text", "text": "EPISTEMIC_INPUT\n" + canonical_json(document)}
        )
        request = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": self.max_tokens,
            "thinking_budget_tokens": self.thinking_budget_tokens,
            "response_format": _response_schema(
                basis_aliases=[alias_by_id[value] for value in eligible_basis_ids],
                predicates=observed_predicates,
                revision_target_alias=(
                    None
                    if revision_target_id is None
                    else alias_by_id[revision_target_id]
                ),
                criticism_alias=(
                    None if criticism is None else alias_by_id[criticism.object_id]
                ),
            ),
        }
        return QwenTurn(
            request_id=request_id,
            basis_revision=cognition.epistemic.revision,
            frontier=frontier,
            document=document,
            request=request,
            visible_object_ids=frozenset(
                alias_by_id[object_id] for object_id in frontier.object_ids
            ),
            alias_to_object_id=alias_to_id,
            next_orientation=QwenOrientation(
                cursor=cognition.epistemic.revision,
                turn_index=orientation.turn_index + 1,
            ),
        )

    @staticmethod
    def _response_text(response: Mapping[str, Any]) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise QwenWorkerError("completion has no assistant content") from exc
        if not isinstance(content, str) or not content.strip():
            raise QwenWorkerError("completion content is empty")
        return content

    def compile_response(
        self, turn: QwenTurn, response: Mapping[str, Any]
    ) -> QwenCompilation:
        response_id = str(response.get("id", f"response:{content_hash(response)}"))
        try:
            body = json.loads(self._response_text(response))
        except json.JSONDecodeError as exc:
            return QwenCompilation(
                False,
                False,
                None,
                None,
                None,
                response_id,
                f"invalid-json:{exc.msg}",
            )
        if not isinstance(body, dict):
            return QwenCompilation(
                False, False, None, None, None, response_id, "response-not-object"
            )
        if body.get("protocol") != PROTOCOL or body.get("request_id") != turn.request_id:
            return QwenCompilation(
                False, False, None, None, None, response_id, "contract-mismatch"
            )
        proposal_body = body.get("proposal")
        abstain = body.get("abstain") is True
        if abstain == (proposal_body is not None):
            return QwenCompilation(
                False,
                abstain,
                None,
                None,
                None,
                response_id,
                "choose-proposal-xor-abstain",
            )
        if abstain:
            return QwenCompilation(True, True, None, None, None, response_id)
        if not isinstance(proposal_body, dict):
            return QwenCompilation(
                False, False, None, None, None, response_id, "proposal-not-object"
            )
        try:
            atoms: list[SourceAtom] = []
            for atom in proposal_body["conditions"]:
                atoms.append((str(atom["predicate"]), tuple(atom["arguments"])))
            conditions = tuple(atoms)
            mapping = canonical_variable_ordinals(conditions)
            effect_names = tuple(proposal_body["effect_arguments"])
            effect_variables = (mapping[effect_names[0]], mapping[effect_names[1]])
            basis_aliases = tuple(proposal_body["basis_ids"])
            revises_alias = proposal_body.get("revises_id")
            criticism_alias = proposal_body.get("criticism_id")
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            return QwenCompilation(
                False,
                False,
                None,
                None,
                None,
                response_id,
                f"proposal-shape:{exc}",
            )
        references = {*basis_aliases}
        if revises_alias is not None:
            references.add(str(revises_alias))
        if criticism_alias is not None:
            references.add(str(criticism_alias))
        if not references.issubset(turn.visible_object_ids):
            return QwenCompilation(
                False, False, None, None, None, response_id, "invisible-reference"
            )
        basis_ids = tuple(turn.alias_to_object_id[value] for value in basis_aliases)
        revises_id = (
            None
            if revises_alias is None
            else turn.alias_to_object_id[str(revises_alias)]
        )
        criticism_id = (
            None
            if criticism_alias is None
            else turn.alias_to_object_id[str(criticism_alias)]
        )
        try:
            proposal = SemanticSchemaProposal(
                name=str(proposal_body["name"]),
                conditions=conditions,
                operator=str(proposal_body["operator"]),
                measure=str(proposal_body["measure"]),
                effect_variables=effect_variables,
                basis_ids=basis_ids,
            )
        except (SharedCognitionError, TypeError, ValueError) as exc:
            return QwenCompilation(
                False, False, None, None, None, response_id, f"semantic:{exc}"
            )
        return QwenCompilation(
            valid=True,
            abstained=False,
            proposal=proposal,
            revises_id=None if revises_id is None else str(revises_id),
            criticism_id=None if criticism_id is None else str(criticism_id),
            response_id=response_id,
        )

    def think(
        self,
        cognition: NativeSharedCognition,
        *,
        orientation: QwenOrientation,
        request_id: str,
        current_frame: Grid,
        previous_frame: Grid | None = None,
        transition: Mapping[str, Any] | None = None,
    ) -> QwenIntegration:
        turn = self.build_turn(
            cognition,
            orientation=orientation,
            request_id=request_id,
            current_frame=current_frame,
            previous_frame=previous_frame,
            transition=transition,
        )
        response = self.poster(self.endpoint, turn.request, self.timeout_seconds)
        compilation = self.compile_response(turn, response)
        if not compilation.valid:
            raise QwenWorkerError(compilation.rejection or "semantic compilation failed")
        grounded = None
        if compilation.proposal is not None:
            try:
                grounded = cognition.propose(
                    compilation.proposal,
                    response_id=compilation.response_id,
                    revises_id=compilation.revises_id,
                    criticism_id=compilation.criticism_id,
                )
            except SharedCognitionError as exc:
                if "alpha-identical revision" not in str(exc):
                    raise
                dependencies = tuple(
                    dict.fromkeys(
                        (
                            *compilation.proposal.basis_ids,
                            *(
                                ()
                                if compilation.revises_id is None
                                else (compilation.revises_id,)
                            ),
                            *(
                                ()
                                if compilation.criticism_id is None
                                else (compilation.criticism_id,)
                            ),
                        )
                    )
                )
                attempt = cognition.epistemic.add_object(
                    kind="qwen-revision-attempt",
                    semantic_key={"response_id": compilation.response_id},
                    payload={
                        "response_id": compilation.response_id,
                        "revises_id": compilation.revises_id,
                        "conditions": [
                            [head, list(arguments)]
                            for head, arguments in compilation.proposal.conditions
                        ],
                        "status": "rejected-alpha-repeat",
                    },
                    creator="qwen",
                    dependency_ids=dependencies,
                )
                criticism = cognition.epistemic.add_object(
                    kind="structured-criticism",
                    semantic_key={
                        "attempt": attempt.object_id,
                        "target": compilation.revises_id,
                        "status": "alpha-repeat",
                    },
                    payload={
                        "target": compilation.revises_id,
                        "status": "alpha-repeat",
                        "instruction": "change relational conditions; reordering or renaming is not revision",
                    },
                    creator="kernel",
                    dependency_ids=tuple(
                        value
                        for value in (attempt.object_id, compilation.revises_id)
                        if value is not None
                    ),
                )
                cognition.epistemic.attend(
                    worker="qwen",
                    object_id=criticism.object_id,
                    weight=900,
                    channel="compiler-criticism",
                    basis_ids=(attempt.object_id,),
                    nonce=compilation.response_id,
                )
        return QwenIntegration(
            compilation=compilation,
            grounded=grounded,
            orientation=turn.next_orientation,
        )
