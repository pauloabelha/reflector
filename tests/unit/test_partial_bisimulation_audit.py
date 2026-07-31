from scripts.audit_partial_bisimulation import (
    ProspectiveAudit,
    causal_outcome,
    compatible_profiles,
)


def test_compatible_partial_profiles_require_shared_commuting_role() -> None:
    motion = {("move",): {("motion",)}}
    extension = {
        ("move",): {("motion",)},
        ("click",): {("structural",)},
    }
    conflict = {("move",): {("phase",)}}
    disjoint = {("click",): {("structural",)}}

    assert compatible_profiles(motion, extension)
    assert not compatible_profiles(motion, conflict)
    assert not compatible_profiles(motion, disjoint)


def test_prospective_profile_transfer_confirms_untried_role() -> None:
    audit = ProspectiveAudit()
    domain = (1, 2)
    audit.observe(
        source="donor",
        domain=domain,
        role=("move",),
        outcome=("motion",),
    )
    audit.observe(
        source="donor",
        domain=domain,
        role=("click",),
        outcome=("structural",),
    )
    audit.observe(
        source="recipient",
        domain=domain,
        role=("move",),
        outcome=("motion",),
    )
    audit.observe(
        source="recipient",
        domain=domain,
        role=("click",),
        outcome=("structural",),
    )

    assert audit.predictions == 1
    assert audit.confirmations == 1
    assert audit.conflicts == 0
    assert audit.abstract_frontier_roles == 1


def test_causal_outcome_discards_render_novelty_but_retains_structure() -> None:
    transition = {
        "result": [
            "frame_changed(scene)",
            "novel_state_reached(scene)",
            "object_appeared(o1)",
            "object_moved(o2,1,0)",
        ]
    }

    assert causal_outcome(transition, terminal=False) == (
        "structural",
        "motion",
    )
    assert causal_outcome(transition, terminal=True) == ("terminal",)
