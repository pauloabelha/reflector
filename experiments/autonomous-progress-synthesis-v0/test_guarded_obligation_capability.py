import json
import pytest

import guarded_obligation_capability as guarded


def world(*, relabel=False, incomplete=False):
    # Two branches: visiting x changes the visible register, after which the
    # guarded site g becomes satisfiable.  Opaque action IDs are arbitrary.
    left, right, up, down = ((91, 7, 44, 3) if relabel else (1, 2, 3, 4))
    edges = (
        ("s", right, "j"), ("j", left, "s"),
        ("j", up, "x"), ("x", down, "j"),
        ("j", right, "g"), ("g", left, "j"),
    )
    return guarded.GuardedWorld(
        start_node="s",
        start_register=("round", "light"),
        transitions=edges,
        obligations=(guarded.GuardedObligation("o0", "g", ("angular", "light")),),
        arrival_effects=() if incomplete else (
            guarded.ArrivalEffect(
                "x", ("round", "light"), ("angular", "light"), ("transition:t7",)
            ),
        ),
        unexplored_transformer_nodes=("x",) if incomplete else (),
        basis_ids=("frame:f0", "relation:r0"),
    )


def test_shortest_plan_requires_state_change_before_guarded_visit():
    capability = guarded.compile_capability(world())
    plan = guarded.plan_capability(capability)
    assert plan.complete and plan.mode == "control"
    assert plan.visited_nodes == ("s", "j", "x", "j", "g")
    assert plan.actions == (2, 3, 4, 2)
    assert plan.discharged == ("o0",)
    assert plan.register_trace[-1] == ("angular", "light")
    assert capability.empirical_support == 0


def test_opaque_action_relabeling_changes_commands_not_semantics():
    plain = guarded.plan_capability(guarded.compile_capability(world()))
    relabeled = guarded.plan_capability(guarded.compile_capability(world(relabel=True)))
    assert relabeled.visited_nodes == plain.visited_nodes
    assert relabeled.register_trace == plain.register_trace
    assert relabeled.actions == (7, 44, 3, 7)
    assert guarded.compile_capability(world()).candidate_id == guarded.compile_capability(world(relabel=True)).candidate_id


def test_unknown_transformer_yields_probe_not_fabricated_control():
    plan = guarded.plan_capability(guarded.compile_capability(world(incomplete=True)))
    assert not plan.complete and plan.mode == "probe-transformer"
    assert plan.visited_nodes == ("s", "j", "x")
    assert plan.actions == (2, 3)
    assert plan.discharged == ()


def test_multiple_obligations_are_planned_in_joint_pose_register_state():
    base = world()
    expanded = guarded.GuardedWorld(
        start_node=base.start_node,
        start_register=base.start_register,
        transitions=base.transitions + (("s", 8, "h"), ("h", 9, "s")),
        obligations=(
            guarded.GuardedObligation("o0", "g", ("angular", "light")),
            guarded.GuardedObligation("o1", "h", ("round", "light")),
        ),
        arrival_effects=base.arrival_effects + (
            guarded.ArrivalEffect("s", ("angular", "light"), ("round", "light"), ("transition:t8",)),
        ),
        basis_ids=base.basis_ids,
    )
    plan = guarded.plan_capability(guarded.compile_capability(expanded))
    assert plan.complete
    assert set(plan.discharged) == {"o0", "o1"}
    # Search chooses the globally shortest ordering rather than the order in
    # which obligations happened to be declared.
    assert "h" in plan.visited_nodes and "g" in plan.visited_nodes
    assert plan.visited_nodes.index("h") < plan.visited_nodes.index("g")


def test_conflicting_direct_effects_are_rejected():
    base = world()
    conflict = guarded.GuardedWorld(
        base.start_node, base.start_register, base.transitions, base.obligations,
        base.arrival_effects + (
            guarded.ArrivalEffect("x", base.start_register, ("other",), ("transition:bad",)),
        ),
        basis_ids=base.basis_ids,
    )
    with pytest.raises(guarded.GuardedObligationError, match="conflicting"):
        guarded.plan_capability(guarded.compile_capability(conflict))


def test_only_environment_evidence_changes_support():
    capability = guarded.compile_capability(world())
    plan = guarded.plan_capability(capability)
    with pytest.raises(guarded.GuardedObligationError, match="environment"):
        guarded.GuardedEvidence(
            capability.candidate_id, capability.binding_id, "transition:t9", 0, 0, True, actor="qwen"
        )
    confirmed = guarded.adjudicate(capability, guarded.GuardedEvidence(
        capability.candidate_id, capability.binding_id, "transition:t9", 0, 0, True
    ))
    assert confirmed.empirical_support == 10 and confirmed.confirmations == 1
    refuted = guarded.adjudicate(confirmed, guarded.GuardedEvidence(
        capability.candidate_id, capability.binding_id, "transition:t10", 0, 1, True
    ))
    assert refuted.empirical_support == 0 and refuted.refutations == 1
    assert plan.complete


def test_transferable_document_contains_no_situated_policy():
    capability = guarded.compile_capability(world(relabel=True))
    public = guarded.workspace_document(capability)
    text = json.dumps(public, sort_keys=True).lower()
    assert "start_node" not in text and "required_register" not in text
    assert "transitions" not in text and "opaque_action" not in text
    assert public["payload"]["empirical_support"] == 0
    situated = guarded.workspace_document(capability, include_binding=True)
    assert situated["binding"]["transitions"]
    assert situated["binding"]["arrival_effects"][0]["evidence_ids"] == ["transition:t7"]


def test_induces_topology_and_arrival_effect_from_grounded_transitions():
    obligation = guarded.GuardedObligation("o0", "g", ("angular", "light"))
    def obs(name, node, register):
        return guarded.GuardedObservation(name, node, register, (obligation,))
    s = obs("frame:s", "s", ("round", "light"))
    j = obs("frame:j", "j", ("round", "light"))
    x = obs("frame:x", "x", ("angular", "light"))
    j_after = obs("frame:j-after", "j", ("angular", "light"))
    g = obs("frame:g", "g", ("angular", "light"))
    rows = (
        guarded.GuardedTransition("transition:1", s, 17, j),
        guarded.GuardedTransition("transition:2", j, 29, x),
        guarded.GuardedTransition("transition:3", x, 31, j_after),
        guarded.GuardedTransition("transition:4", j_after, 17, g),
    )
    capability = guarded.induce_from_transitions(s, rows)
    plan = guarded.plan_capability(capability)
    assert plan.complete and plan.actions == (17, 29, 31, 17)
    assert capability.empirical_support == 0
    assert "transition:2" in plan.basis_ids


def test_induction_ignores_indirect_state_change_and_then_probes_candidate():
    obligation = guarded.GuardedObligation("o0", "g", ("angular",))
    s = guarded.GuardedObservation("frame:s", "s", ("round",), (obligation,), ("x",))
    x = guarded.GuardedObservation("frame:x", "x", ("angular",), (obligation,), ("x",))
    capability = guarded.induce_from_transitions(
        s, (
            guarded.GuardedTransition("transition:stay", s, 6, s),
            guarded.GuardedTransition("transition:occluded", s, 5, x, direct=False),
        )
    )
    # Indirect evidence creates neither an executable edge nor a trusted state
    # transformer, so it cannot fabricate a plan.
    plan = guarded.plan_capability(capability)
    assert plan.mode == "unreachable" and plan.actions == ()
