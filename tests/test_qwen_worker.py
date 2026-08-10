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
from reflector2.shared_cognition import NativeSharedCognition


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
                                    "measure": "RelationalResidual",
                                    "effect_arguments": ["?left", "?right"],
                                    "basis_ids": [observation_alias],
                                    "revises_id": None,
                                    "criticism_id": None,
                                },
                                "abstain": False,
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


def test_png_encoder_is_deterministic() -> None:
    first = grid_png_data_url(((0, 1), (2, 3)))
    second = grid_png_data_url(((0, 1), (2, 3)))
    assert first == second
    assert len(first) > 100
    assert grid_png_data_url(((10, 11),)) == grid_png_data_url(((10, 11),))
    assert grid_png_data_url(((10, 11),)) != grid_png_data_url(((11, 10),))
