import json
from pathlib import Path

from scripts.audit_causal_version_space import audit_root


def _event(
    *,
    digest: str,
    decision_action: int,
    transition_action: int | None = None,
    result: list[str] | None = None,
) -> dict[str, object]:
    transition: dict[str, object] = {}
    if transition_action is not None:
        transition = {
            "action_id": transition_action,
            "action_data": {},
            "context": ["action_available(1)", "action_available(2)"],
            "result": result or [],
        }
    return {
        "observation": {
            "frame_digest": digest,
            "levels_completed": 0,
            "state": "NOT_FINISHED",
        },
        "decision": {
            "action_id": decision_action,
            "data": {},
            "reason": "epistemic-frontier:untried-current-state",
        },
        "transition": transition,
    }


def test_ambiguous_query_eliminates_incompatible_donor_outcome(
    tmp_path: Path,
) -> None:
    events = (
        _event(digest="donor-a", decision_action=1),
        _event(
            digest="donor-a",
            decision_action=2,
            transition_action=1,
            result=["object_moved(o1,1,0)"],
        ),
        _event(
            digest="donor-b",
            decision_action=1,
            transition_action=2,
            result=["object_appeared(o2)"],
        ),
        _event(
            digest="donor-b",
            decision_action=2,
            transition_action=1,
            result=["object_moved(o1,1,0)"],
        ),
        _event(
            digest="recipient",
            decision_action=1,
            transition_action=2,
            result=["state_changed(scene)"],
        ),
        _event(
            digest="recipient",
            decision_action=2,
            transition_action=1,
            result=["object_moved(o1,1,0)"],
        ),
        _event(
            digest="after-query",
            decision_action=1,
            transition_action=2,
            result=["object_appeared(o2)"],
        ),
    )
    stream = tmp_path / "synthetic.cognitive.jsonl"
    stream.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )

    result = audit_root(tmp_path)
    cegis = result["results"]["synthetic"]["cegis"]

    assert cegis["opportunity_states"] == 1
    assert cegis["opportunity_roles"] == 1
    assert cegis["executed_ambiguous_queries"] == 1
    assert cegis["donor_hypotheses"] == 2
    assert cegis["eliminated_hypotheses"] == 1
    assert cegis["queries_with_elimination"] == 1
    assert cegis["generic_queries"] == 1
