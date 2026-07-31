from reflector.core.reference_constellation import (
    _unbounded_central_completion,
)


def test_unbounded_completion_recovers_boundary_clipped_arm() -> None:
    anchor = (54, 36)
    visible = frozenset(
        {(x, 36) for x in range(41, 64)}
        | {(54, y) for y in range(23, 50)}
    )

    completed = _unbounded_central_completion(visible, anchor)

    assert (67, 36) in completed
    assert (54, 23) in completed
    assert (54, 49) in completed
