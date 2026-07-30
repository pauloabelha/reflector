from __future__ import annotations

import json

import pytest

from reflector.core.exploration import EpistemicExplorer
from reflector.core.inheritance import (
    EMPTY_SCHEME_LIBRARY_ROOT,
    SchemeDefinition,
    SchemeLibrary,
    starter_scheme_library,
)
from reflector.core.mind import MindConfig
from reflector.core.perception import SceneTracker
from reflector.core.symbolic import Observation
from reflector.evolution.evolver import descendants, root_candidate
from reflector.evolution.inheritance import (
    SchemeEvidence,
    SchemeEvidenceLedger,
    SchemePromotionRule,
    accommodate_scheme,
    config_with_scheme_library,
    promoted_library,
)
from reflector.evolution.mutations import (
    DeterministicMutationProvider,
    MutationProposal,
)


def _definition(name: str = "transport") -> SchemeDefinition:
    return SchemeDefinition(
        name=name,
        operator="transform",
        parameters=("direction", "object"),
        grounding=("action-family", "object"),
        preconditions=("controllable(object)",),
        effects=("translated(object,direction)",),
        invariants=("shape(object)",),
        goal_contract=("decreases(target_distance)",),
        falsifiers=("predicted-translation-absent",),
        resource_cap=8,
        complexity_cost=5,
    )


def _evidence(
    definition: SchemeDefinition,
    outcome: str,
    *,
    partition: str,
    suffix: str,
) -> SchemeEvidence:
    return SchemeEvidence(
        scheme_id=definition.scheme_id,
        candidate_id="candidate-test",
        partition=partition,
        episode_digest=f"episode-{suffix}",
        prediction_digest=f"prediction-{suffix}",
        outcome=outcome,  # type: ignore[arg-type]
        interventions_saved=1,
    )


def test_scheme_hash_is_canonical_and_excludes_evidence() -> None:
    definition = _definition()
    restored = SchemeDefinition.from_json(definition.to_json())

    assert restored == definition
    assert restored.scheme_id == definition.scheme_id
    assert len(definition.scheme_id) == 64

    noncanonical = json.dumps(definition.to_dict(), indent=2)
    with pytest.raises(ValueError, match="canonical"):
        SchemeDefinition.from_json(noncanonical)

    first = _evidence(
        definition,
        "prediction-confirmed",
        partition="development:a",
        suffix="a",
    )
    second = _evidence(
        definition,
        "prediction-falsified",
        partition="development:b",
        suffix="b",
    )
    assert first.scheme_id == second.scheme_id == definition.scheme_id
    assert first.evidence_id != second.evidence_id


def test_library_is_merkle_closed_and_accommodation_preserves_parent() -> None:
    parent = _definition()
    accommodated = accommodate_scheme(
        parent,
        preconditions=(
            "controllable(object)",
            "phase(open)",
        ),
    )
    library = SchemeLibrary.create((accommodated, parent))

    assert accommodated.scheme_id != parent.scheme_id
    assert accommodated.dependencies == (parent.scheme_id,)
    assert library.root != EMPTY_SCHEME_LIBRARY_ROOT
    assert SchemeLibrary.from_json_definitions(
        library.json_definitions()
    ) == library
    with pytest.raises(ValueError, match="missing dependencies"):
        SchemeLibrary.create((accommodated,))


def test_evidence_merge_is_idempotent_and_promotion_keeps_dependencies() -> None:
    parent = _definition()
    child = accommodate_scheme(
        parent,
        name="phase-conditioned-transport",
        preconditions=("controllable(object)", "phase(open)"),
    )
    proposals = SchemeLibrary.create((parent, child))
    events = (
        _evidence(
            child,
            "prediction-confirmed",
            partition="development:a",
            suffix="a",
        ),
        _evidence(
            child,
            "prediction-confirmed",
            partition="heldout:b",
            suffix="b",
        ),
        _evidence(
            child,
            "level-progress",
            partition="heldout:b",
            suffix="c",
        ),
    )
    first = SchemeEvidenceLedger.create(events[:2])
    ledger = first.merge(SchemeEvidenceLedger.create(events[1:]))
    accepted = promoted_library(proposals, ledger)

    assert len(ledger.events) == 3
    assert {item.scheme_id for item in accepted.definitions} == {
        parent.scheme_id,
        child.scheme_id,
    }

    falsified = ledger.append(
        _evidence(
            child,
            "prediction-falsified",
            partition="heldout:c",
            suffix="d",
        )
    )
    assert not SchemePromotionRule().accepts(child.scheme_id, falsified)


def test_exact_library_snapshot_round_trips_and_is_inherited_by_offspring() -> None:
    library = starter_scheme_library()
    config = config_with_scheme_library(MindConfig(), library)
    restored = MindConfig.from_dict(
        json.loads(json.dumps(config.to_dict()))
    )
    parent = root_candidate(restored)
    provider = DeterministicMutationProvider(
        MutationProposal(
            {"information_weight": 2.0},
            "change exploration pressure without changing inherited knowledge",
        )
    )
    (child,) = descendants(parent, (provider,), {})

    assert restored == config
    assert restored.enable_preregistered_structural_credit
    assert child.config.inherited_scheme_root == library.root
    assert (
        child.config.inherited_scheme_definitions
        == library.json_definitions()
    )
    assert child.candidate_id != parent.candidate_id

    invalid = config.to_dict()
    invalid["inherited_scheme_root"] = "0" * 64
    with pytest.raises(ValueError, match="does not match"):
        MindConfig.from_dict(invalid)

    disabled_credit = config.to_dict()
    disabled_credit["enable_preregistered_structural_credit"] = False
    with pytest.raises(ValueError, match="requires preregistered"):
        MindConfig.from_dict(disabled_credit)


def test_inherited_schemes_enter_operative_structural_credit() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
    )
    scene, _events = SceneTracker().perceive(observation)
    library = starter_scheme_library()
    explorer = EpistemicExplorer(inherited_scheme_library=library)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 1), ("y", 1))
    assert explorer.last_scheme_components
    assert all(
        component.startswith("scheme:inherited:")
        for component in explorer.last_scheme_components
    )
    telemetry = explorer.to_dict()
    assert telemetry["inherited_scheme_count"] == len(library.definitions)
    assert telemetry["inherited_scheme_root"] == library.root
