import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import capability_registry as registry
from test_route_option import frame
from test_progress_synthesis import placement_grid

def test_registry_discovers_route_without_a_game_selector():
    initial=frame((3,3));rows=registry.propose(initial,{41:frame((9,3)),42:frame((3,9)),43:frame((3,3))})
    route=[row for row in rows if row.capability=="interactive:conditional-route"]
    assert len(route)==1 and route[0].empirical_support==0 and route[0].interactive

def test_registry_does_not_emit_unknown_capabilities_on_blank_world():
    blank=[[0]*12 for _ in range(12)]
    assert registry.propose(blank,{1:blank,2:blank})==()


def test_registry_compiles_from_live_calibrated_action_laws_without_resets():
    rows=registry.propose_calibrated(
        placement_grid(),
        motion_actions={(-1,0):73,(1,0):11,(0,-1):41,(0,1):29},
        parameterized_actions=(97,),
    )
    assignments=[row for row in rows if row.capability=="exact:UnassignedMemberCount"]
    assert assignments and assignments[0].empirical_support==0
    assert assignments[0].execution.proposal.commands
    assert {command.opaque_action for command in assignments[0].execution.proposal.commands}<={73,11,41,29,97}
