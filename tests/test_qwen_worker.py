from __future__ import annotations

import json

from reflector2.perception import PerceptionBatch
from reflector2.qwen_worker import (
    PROTOCOL,
    QwenOrientation,
    QwenSemanticWorker,
    grid_png_data_url,
)
from reflector2.runtime import Runtime
from reflector2.shared_cognition import NativeSharedCognition, SemanticSchemaProposal


def _batch(runtime: Runtime) -> PerceptionBatch:
    terms = runtime.graph.terms
    left = terms.intern_symbol("entity:left")
    right = terms.intern_symbol("entity:right")
    relation = terms.intern_symbol("SameStructure")
    return PerceptionBatch(
        context="frame:0",
        facts=((relation, (left, right)),),
        form_terms=(),
        region_terms=(left, right),
        source="sensor:grid",
    )


def _ambiguous_batch(runtime: Runtime) -> PerceptionBatch:
    terms = runtime.graph.terms
    left = terms.intern_symbol("entity:left")
    middle = terms.intern_symbol("entity:middle")
    right = terms.intern_symbol("entity:right")
    related = terms.intern_symbol("Related")
    distinguishes = terms.intern_symbol("Distinguishes")
    return PerceptionBatch(
        context="frame:ambiguous",
        facts=(
            (related, (left, middle)),
            (related, (left, right)),
            (distinguishes, (left, middle)),
        ),
        form_terms=(),
        region_terms=(left, middle, right),
        source="sensor:grid",
    )


def test_visual_turn_contains_direct_frames_and_shared_frontier() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    cognition.observe(_batch(runtime))
    worker = QwenSemanticWorker(poster=lambda *_args: {})
    frame = ((0, 1), (2, 3))

    turn = worker.build_turn(
        cognition,
        orientation=QwenOrientation(),
        request_id="request:0",
        current_frame=frame,
        previous_frame=((0, 0), (1, 1)),
        transition={"intervention_ref": "opaque:i0", "changed": True},
    )

    content = turn.request["messages"][0]["content"]
    images = [item for item in content if item["type"] == "image_url"]
    assert len(images) == 2
    assert all(
        item["image_url"]["url"].startswith("data:image/png;base64,")
        for item in images
    )
    assert turn.document["workspace"]["frontier"]
    assert turn.next_orientation.cursor == cognition.epistemic.revision
    index = turn.document["deltas"]["authoritative_index"]
    assert len(index["kind_codes"]) == index["object_count"]
    assert len(index["creator_codes"]) == index["object_count"]
    assert len(index["semantic_payload_digest4_pairs"]) == index["object_count"]
    assert "kinds" not in index
    assert "creators" not in index


def test_strict_qwen_write_compiles_and_grounds_in_native_r2() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    observation_id = cognition.observe(_batch(runtime))

    def poster(_endpoint, payload, _timeout):
        input_text = payload["messages"][0]["content"][-1]["text"]
        request_id = input_text.split('"request_id":"', 1)[1].split('"', 1)[0]
        document = json.loads(input_text.split("EPISTEMIC_INPUT\n", 1)[1])
        observation_alias = next(
            item["id"]
            for item in document["workspace"]["frontier"]
            if item["kind"] == "observation"
        )
        return {
            "id": "qwen-response:0",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "protocol": PROTOCOL,
                                "request_id": request_id,
                                "proposal": {
                                    "name": "SameStructureProgress",
                                    "conditions": [
                                        {
                                            "predicate": "SameStructure",
                                            "arguments": ["?left", "?right"],
                                        }
                                    ],
                                    "operator": "Decrease",
                                    "measure": "TranslationAlignmentResidual",
                                    "effect_arguments": ["?left", "?right"],
                                    "basis_ids": [observation_alias],
                                    "revises_id": None,
                                    "criticism_id": None,
                                },
                            },
                            separators=(",", ":"),
                        )
                    }
                }
            ],
        }

    worker = QwenSemanticWorker(poster=poster)
    integrated = worker.think(
        cognition,
        orientation=QwenOrientation(),
        request_id="request:0",
        current_frame=((0, 1), (0, 1)),
    )

    assert integrated.compilation.valid
    assert integrated.grounded is not None
    assert integrated.grounded.status == "bound"
    assert runtime.graph.canonical_hash[integrated.grounded.native_schema_id]
    assert cognition.epistemic.object(integrated.grounded.hypothesis_id).creator == "qwen"


def test_worker_rejects_transport_leakage() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    cognition.observe(_batch(runtime))
    worker = QwenSemanticWorker(poster=lambda *_args: {})
    try:
        worker.build_turn(
            cognition,
            orientation=QwenOrientation(),
            request_id="request:bad",
            current_frame=((0, 1),),
            transition={"action_id": 3},
        )
    except Exception as exc:
        assert "forbidden transport identity" in str(exc)
    else:
        raise AssertionError("raw action identity entered Qwen context")


def test_revision_turn_uses_small_exclusive_contract_and_exact_target() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    observation_id = cognition.observe(_ambiguous_batch(runtime))
    initial = cognition.propose(
        SemanticSchemaProposal(
            name="AmbiguousRelation",
            conditions=(("Related", ("?a", "?b")),),
            operator="Decrease",
            measure="TranslationAlignmentResidual",
            effect_variables=(0, 1),
            basis_ids=(observation_id,),
        ),
        response_id="qwen:initial",
    )
    assert initial.status == "ambiguous"
    assert initial.criticism_id is not None

    worker = QwenSemanticWorker(poster=lambda *_args: {})
    turn = worker.build_turn(
        cognition,
        orientation=QwenOrientation(),
        request_id="request:revision",
        current_frame=((0, 1), (0, 1)),
    )
    assert turn.document["revision_task"]["target"]
    schema = turn.request["response_format"]["json_schema"]["schema"]
    assert "oneOf" in schema
    assert "revision" in schema["oneOf"][0]["properties"]
    observation_alias = next(
        item["id"]
        for item in turn.document["workspace"]["frontier"]
        if item["kind"] == "observation"
    )
    target_alias = turn.document["revision_task"]["target"]
    criticism_alias = turn.document["revision_task"]["criticism"]
    response = {
        "id": "qwen:revision",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "protocol": PROTOCOL,
                            "request_id": turn.request_id,
                            "revision": {
                                "name": "UniqueRelationRevision",
                                "conditions": [
                                    {
                                        "predicate": "Related",
                                        "arguments": ["?a", "?b"],
                                    },
                                    {
                                        "predicate": "Distinguishes",
                                        "arguments": ["?a", "?b"],
                                    },
                                ],
                                "operator": "Decrease",
                                "measure": "TranslationAlignmentResidual",
                                "effect_arguments": ["?a", "?b"],
                                "basis_ids": [observation_alias],
                                "revises_id": target_alias,
                                "criticism_id": criticism_alias,
                            },
                        }
                    )
                }
            }
        ],
    }
    compilation = worker.compile_response(turn, response)
    assert compilation.valid
    assert compilation.revises_id == initial.hypothesis_id
    assert compilation.criticism_id == initial.criticism_id


def test_unbound_effect_variable_becomes_visible_compiler_criticism() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    cognition.observe(_batch(runtime))

    def poster(_endpoint, payload, _timeout):
        input_text = payload["messages"][0]["content"][-1]["text"]
        document = json.loads(input_text.split("EPISTEMIC_INPUT\n", 1)[1])
        observation_alias = next(
            item["id"]
            for item in document["workspace"]["frontier"]
            if item["kind"] == "observation"
        )
        return {
            "id": "qwen:unbound-effect",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "protocol": PROTOCOL,
                                "request_id": document["request_id"],
                                "proposal": {
                                    "name": "MalformedUnboundEffect",
                                    "conditions": [
                                        {
                                            "predicate": "SameStructure",
                                            "arguments": ["?a", "?b"],
                                        }
                                    ],
                                    "operator": "Decrease",
                                    "measure": "TranslationAlignmentResidual",
                                    "effect_arguments": ["?a", "?family"],
                                    "basis_ids": [observation_alias],
                                    "revises_id": None,
                                    "criticism_id": None,
                                },
                            }
                        )
                    }
                }
            ],
        }

    worker = QwenSemanticWorker(poster=poster)
    integrated = worker.think(
        cognition,
        orientation=QwenOrientation(),
        request_id="request:malformed",
        current_frame=((0, 1), (0, 1)),
    )

    assert not integrated.compilation.valid
    assert integrated.compilation.rejection == "proposal-shape:'?family'"
    assert integrated.grounded is None
    assert integrated.orientation.turn_index == 1
    criticisms = [
        item
        for item in cognition.epistemic.objects
        if item.kind == "structured-criticism"
        and item.payload.get("status") == "compiler-rejected"
    ]
    assert len(criticisms) == 1
    assert cognition.epistemic.support(criticisms[0].object_id) == 0
    next_turn = worker.build_turn(
        cognition,
        orientation=integrated.orientation,
        request_id="request:repair",
        current_frame=((0, 1), (0, 1)),
    )
    visible_kinds = {
        item["kind"] for item in next_turn.document["workspace"]["frontier"]
    }
    assert "qwen-write-attempt" in visible_kinds
    assert "structured-criticism" in visible_kinds


def test_rolling_turn_compacts_dormant_events_without_duplicating_payloads() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    cognition.observe(_batch(runtime))
    worker = QwenSemanticWorker(root_limit=1, poster=lambda *_args: {})
    first = worker.build_turn(
        cognition,
        orientation=QwenOrientation(),
        request_id="request:initial",
        current_frame=((0, 1), (0, 1)),
    )
    dormant = cognition.epistemic.add_object(
        kind="dormant-note",
        semantic_key={"note": "unselected"},
        payload={"large_semantic_body": "must-stay-in-ledger" * 40},
        creator="r2",
    )
    cognition.epistemic.add_object(
        kind="observation",
        semantic_key={"context": "frame:1"},
        payload={
            "context": "frame:1",
            "facts": [["SameStructure", ["entity:left", "entity:right"]]],
        },
        creator="environment",
    )
    second = worker.build_turn(
        cognition,
        orientation=first.next_orientation,
        request_id="request:rolling",
        current_frame=((0, 1), (0, 1)),
    )

    deltas = second.document["deltas"]
    assert deltas["fidelity"].startswith("mixed compact projection")
    assert deltas["total_event_count"] == 2
    assert any(row[0] == "G" for row in deltas["rows"])
    assert "must-stay-in-ledger" not in json.dumps(deltas)
    assert cognition.epistemic.object(dormant.object_id).payload[
        "large_semantic_body"
    ].startswith("must-stay-in-ledger")


def test_png_encoder_is_deterministic() -> None:
    first = grid_png_data_url(((0, 1), (2, 3)))
    second = grid_png_data_url(((0, 1), (2, 3)))
    assert first == second
    assert len(first) > 100
    assert grid_png_data_url(((10, 11),)) == grid_png_data_url(((10, 11),))
    assert grid_png_data_url(((10, 11),)) != grid_png_data_url(((11, 10),))


def test_context_reservation_rejects_impossible_configuration() -> None:
    try:
        QwenSemanticWorker(
            context_window_tokens=2048,
            max_tokens=2048,
            poster=lambda *_args: {},
        )
    except Exception as exc:
        assert "context reservation" in str(exc)
    else:
        raise AssertionError("impossible completion reserve was accepted")
