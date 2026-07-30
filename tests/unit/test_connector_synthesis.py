from reflector.core.connector_synthesis import (
    Connector,
    ConnectorSynthesisBounds,
    ConnectorSynthesisProblem,
    ConnectorSynthesisStatus,
    ContainerSpec,
    FixedColorSlot,
    Payload,
    VariableSlot,
    synthesize_connector_program,
)

VARIABLE = VariableSlot()


def _solve(
    reference: tuple[int, ...],
    containers: tuple[ContainerSpec, ...],
    *,
    root: str,
    payloads: tuple[int, ...] = (),
    connectors: tuple[Connector, ...] = (),
):
    return synthesize_connector_program(
        ConnectorSynthesisProblem(
            reference=reference,
            containers=containers,
            root=root,
            payloads=payloads,
            connectors=connectors,
        )
    )


def test_synthesizes_one_connector_with_a_fixed_child_prefix() -> None:
    result = _solve(
        (11, 23, 37, 49),
        (
            ContainerSpec("root", (VARIABLE, VARIABLE, VARIABLE)),
            ContainerSpec("child", (FixedColorSlot(23), VARIABLE)),
        ),
        root="root",
        payloads=(11, 23, 37, 49),
        connectors=(Connector("child"),),
    )

    assert result.status is ConnectorSynthesisStatus.UNIQUE
    assert result.plan is not None
    assert result.plan.emissions == (11, 23, 37, 49)
    assert tuple(binding.item for binding in result.plan.bindings) == (
        Payload(11),
        Connector("child"),
        Payload(49),
        Payload(37),
    )
    assert result.plan.unused_payloads == (23,)


def test_reuses_the_same_assigned_child_twice() -> None:
    result = _solve(
        (61, 73, 61),
        (
            ContainerSpec("root", (VARIABLE, VARIABLE, VARIABLE)),
            ContainerSpec("repeatable-child", (FixedColorSlot(61),)),
        ),
        root="root",
        payloads=(73,),
        connectors=(
            Connector("repeatable-child"),
            Connector("repeatable-child"),
        ),
    )

    assert result.status is ConnectorSynthesisStatus.UNIQUE
    assert result.plan is not None
    assert [item.target for item in result.plan.connector_trace] == [
        "repeatable-child",
        "repeatable-child",
    ]
    assert result.explored_assignments == 3


def test_non_emitting_recursion_does_not_poison_a_unique_repeated_child() -> None:
    result = _solve(
        (13, 41, 20, 27, 41, 20, 27, 34, 6),
        (
            ContainerSpec(
                "root",
                (VARIABLE, VARIABLE, VARIABLE, VARIABLE, VARIABLE),
            ),
            ContainerSpec("child", (VARIABLE, VARIABLE, VARIABLE)),
        ),
        root="root",
        payloads=(13, 41, 20, 27, 34, 6),
        connectors=(Connector("child"), Connector("child")),
    )

    assert result.status is ConnectorSynthesisStatus.UNIQUE
    assert result.plan is not None
    assert result.plan.emissions == result.plan.reference
    assert [item.target for item in result.plan.connector_trace] == [
        "child",
        "child",
    ]
    assert result.explored_assignments == 20_160


def test_orders_three_sibling_connectors_by_the_reference() -> None:
    result = _solve(
        (29, 43, 17),
        (
            ContainerSpec("root", (VARIABLE, VARIABLE, VARIABLE)),
            ContainerSpec("west", (FixedColorSlot(17),)),
            ContainerSpec("middle", (FixedColorSlot(29),)),
            ContainerSpec("east", (FixedColorSlot(43),)),
        ),
        root="root",
        connectors=(
            Connector("west"),
            Connector("middle"),
            Connector("east"),
        ),
    )

    assert result.status is ConnectorSynthesisStatus.UNIQUE
    assert result.plan is not None
    assert [item.target for item in result.plan.connector_trace] == [
        "middle",
        "east",
        "west",
    ]
    assert result.plan.visited_containers == ("root", "west", "middle", "east")


def test_synthesizes_a_two_link_container_chain() -> None:
    result = _solve(
        (31, 47),
        (
            ContainerSpec("root", (VARIABLE,)),
            ContainerSpec("middle", (FixedColorSlot(31), VARIABLE)),
            ContainerSpec("leaf", (FixedColorSlot(47),)),
        ),
        root="root",
        connectors=(Connector("middle"), Connector("leaf")),
    )

    assert result.status is ConnectorSynthesisStatus.UNIQUE
    assert result.plan is not None
    assert [item.target for item in result.plan.connector_trace] == [
        "middle",
        "leaf",
    ]


def test_grounded_connector_cost_breaks_equal_emission_chain_segmentations() -> None:
    edge = VariableSlot(connector_cost=12)
    center = VariableSlot(connector_cost=0)
    result = _solve(
        (6, 13, 27, 14, 41, 34, 20),
        (
            ContainerSpec("root", (edge, center, edge)),
            ContainerSpec("middle", (edge, center, edge)),
            ContainerSpec(
                "leaf",
                (edge, FixedColorSlot(14), edge),
            ),
        ),
        root="root",
        payloads=(6, 20, 13, 34, 27, 41),
        connectors=(Connector("middle"), Connector("leaf")),
    )

    assert result.status is ConnectorSynthesisStatus.UNIQUE
    assert result.plan is not None
    assert tuple(
        (binding.container_id, binding.slot_index, binding.item)
        for binding in result.plan.bindings
        if isinstance(binding.item, Connector)
    ) == (
        ("root", 1, Connector("middle")),
        ("middle", 1, Connector("leaf")),
    )
    assert result.semantic_solutions == 5


def test_bounded_cycle_reuses_persistent_assignments_to_reference_horizon() -> None:
    result = _solve(
        (13, 19, 13, 19, 13, 19),
        (
            ContainerSpec("alpha", (FixedColorSlot(13), VARIABLE)),
            ContainerSpec("beta", (FixedColorSlot(19), VARIABLE)),
        ),
        root="alpha",
        connectors=(Connector("alpha"), Connector("beta")),
    )

    assert result.status is ConnectorSynthesisStatus.UNIQUE
    assert result.plan is not None
    assert result.plan.emissions == result.plan.reference
    assert [item.target for item in result.plan.connector_trace] == [
        "beta",
        "alpha",
        "beta",
        "alpha",
        "beta",
    ]
    assert tuple(binding.item for binding in result.plan.bindings) == (
        Connector("beta"),
        Connector("alpha"),
    )


def test_reports_semantic_ambiguity_and_hard_bounds_without_a_plan() -> None:
    ambiguous = _solve(
        (101, 101),
        (
            ContainerSpec("root", (VARIABLE, VARIABLE)),
            ContainerSpec("west", (FixedColorSlot(101),)),
            ContainerSpec("east", (FixedColorSlot(101),)),
        ),
        root="root",
        connectors=(Connector("west"), Connector("east")),
    )
    bounded = synthesize_connector_program(
        ConnectorSynthesisProblem(
            reference=(5, 7),
            containers=(ContainerSpec("root", (VARIABLE, VARIABLE)),),
            root="root",
            payloads=(5, 7),
            connectors=(),
        ),
        bounds=ConnectorSynthesisBounds(max_assignments=1),
    )

    assert ambiguous.status is ConnectorSynthesisStatus.AMBIGUOUS
    assert ambiguous.plan is None
    assert ambiguous.semantic_solutions == 2
    assert bounded.status is ConnectorSynthesisStatus.BOUNDS_EXCEEDED
    assert bounded.plan is None
    assert bounded.diagnostic == "assignment-enumeration-bound"


def test_rejects_an_acyclic_reference_that_is_only_an_emission_prefix() -> None:
    result = _solve(
        (1,),
        (ContainerSpec("root", (VARIABLE, VARIABLE)),),
        root="root",
        payloads=(1, 2),
    )

    assert result.status is ConnectorSynthesisStatus.NO_SOLUTION
    assert result.plan is None
    assert result.semantic_solutions == 0
