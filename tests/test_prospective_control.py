from __future__ import annotations

from reflector2.perception import perceive_grid
from reflector2.prospective_control import NativeProspectiveController
from reflector2.runtime import Runtime
from reflector2.shared_cognition import NativeSharedCognition, SemanticSchemaProposal


def _frame(ax: int) -> tuple[tuple[int, ...], ...]:
    points = {(ax, 1), (7, 1), (9, 6)}
    return tuple(
        tuple(2 if (x, y) in points else 0 for x in range(11))
        for y in range(8)
    )


def _observe(cognition: NativeSharedCognition, frame, index: int) -> str:
    batch = perceive_grid(
        cognition.runtime.graph.terms,
        frame,
        f"prospective:{index}",
        background=0,
    )
    return cognition.observe(batch)


def test_native_visual_probe_revision_confirmation_and_control() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    observation = _observe(cognition, _frame(1), 0)
    initial = cognition.propose(
        SemanticSchemaProposal(
            name="RepeatedPairPotential",
            conditions=(("SameOutline", ("?a", "?b")),),
            operator="Decrease",
            measure="TranslationAlignmentResidual",
            effect_variables=(0, 1),
            basis_ids=(observation,),
        ),
        response_id="qwen:initial",
    )
    assert initial.status == "ambiguous"
    assert len(initial.effect_pairs) == 3

    controller = NativeProspectiveController(cognition)
    controller.activate(initial, _frame(1))

    # Ordinary fallback supplies action-effect calibration but no epistemic
    # support. Once outcomes differ across alternatives, R2 chooses a genuine
    # prospective discrimination probe.
    first = controller.plan((1, 2))
    assert first.mode == "fallback"
    controller.observe(1, _frame(1), _frame(2), transition_id="transition:0")
    probe = controller.plan((1, 2))
    assert probe.mode == "probe"
    assert probe.commitments
    controller.observe(1, _frame(2), _frame(3), transition_id="transition:1")

    criticism = next(
        item
        for item in reversed(cognition.epistemic.objects)
        if item.kind == "structured-criticism"
    )
    current_observation = _observe(cognition, _frame(3), 2)
    revision = cognition.propose(
        SemanticSchemaProposal(
            name="HorizontallyGroundedPotential",
            conditions=(("AlignedHorizontal", ("?a", "?b")),),
            operator="Decrease",
            measure="TranslationAlignmentResidual",
            effect_variables=(0, 1),
            basis_ids=(current_observation, criticism.object_id),
        ),
        response_id="qwen:revision",
        revises_id=initial.hypothesis_id,
        criticism_id=criticism.object_id,
    )
    assert revision.status == "bound"
    controller.activate(revision, _frame(3))

    confirmation = controller.plan((1, 2))
    assert confirmation.reason == "unique-revision-confirmation"
    controller.observe(1, _frame(3), _frame(4), transition_id="transition:2")
    control = controller.plan((1, 2))
    assert control.mode == "control", {
        "report": controller.report(),
        "confirmation_support": cognition.epistemic.evidence_counts(
            confirmation.commitments[0].prediction_id
        ),
        "prediction": cognition.epistemic.object(
            confirmation.commitments[0].prediction_id
        ).payload,
    }
    assert control.action_id == 1
    assert control.fallback_action_id == 2
