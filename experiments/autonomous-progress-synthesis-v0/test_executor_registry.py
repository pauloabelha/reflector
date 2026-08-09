from executor_registry import compile_execution
from progress_synthesis import synthesize
from test_progress_synthesis import flow_grid,placement_grid


def test_ast_dispatches_flow_without_game_identity():
    grid=flow_grid();candidate=next(c for c in synthesize(grid) if c.ast["potential"]["type"]=="UnservedTerminalCount")
    proposal=compile_execution(candidate,grid,motion_actions={(-1,0):3,(1,0):4,(0,-1):1,(0,1):2},release_actions=(5,))
    assert proposal.complete and proposal.expected_after==0
    assert tuple(command.opaque_action for command in proposal.commands)==(4,4,4,5)


def test_ast_dispatches_assignment_without_game_identity():
    grid=placement_grid();candidate=next(c for c in synthesize(grid) if c.ast["potential"]["type"]=="UnassignedMemberCount")
    proposal=compile_execution(candidate,grid,motion_actions={(-1,0):3,(1,0):4,(0,-1):1,(0,1):2},parameterized_actions=(6,))
    assert proposal.complete and proposal.expected_after==0
    assert proposal.commands and {command.role for command in proposal.commands}>={"select","move"}
