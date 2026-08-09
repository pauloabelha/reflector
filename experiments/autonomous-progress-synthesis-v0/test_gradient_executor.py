import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import compositional_dsl as dsl
import gradient_executor as gradient
import progress_synthesis as ps


def grid(ax=2):
    g=[[0]*14 for _ in range(10)]
    for y in range(2,4):
        for x in range(ax,ax+2):g[y][x]=1
    for y in range(2,4):
        for x in range(10,12):g[y][x]=2
    return g


def candidate():
    scene=ps.perceive(grid());regions=scene.regions
    return dsl.compile_candidate({"op":"BoundingBoxGap","arguments":["?moving","?target"]},{"?moving":regions[0].region_id,"?target":regions[1].region_id},scene)


def test_motion_correspondence_is_role_specific_and_action_opaque():
    moved=gradient.moved_variables(candidate(),grid(),grid(4))
    assert moved=={"?moving":(1,0)}


def test_gradient_plan_constructs_a_multi_step_progress_option():
    plan=gradient.plan(candidate(),grid(),movable_variable="?moving",motion_actions={(-1,0):3,(1,0):4,(0,-1):1,(0,1):2})
    assert plan.predicted_value<plan.start_value
    assert len(plan.opaque_actions)>1 and set(plan.opaque_actions)=={4}
