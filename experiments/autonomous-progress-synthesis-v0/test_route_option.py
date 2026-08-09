import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import route_option

def frame(anchor):
    g=[[5]*19 for _ in range(19)]
    for x,y in ((6,3),(9,6),(9,12),(12,15)):g[y][x]=2
    for y in range(3):
        for x in range(3):g[anchor[1]+y][anchor[0]+x]=9;g[15+y][15+x]=14
    return g

def test_route_option_compiles_from_opaque_reset_successors():
    initial=frame((3,3));successors={41:frame((9,3)),42:frame((3,9)),43:frame((3,3))}
    option=route_option.compile_option(initial,successors)
    assert option.goal_ast["potential"]["type"]=="RemainingRouteSteps"
    assert option.opaque_actions and set(option.opaque_actions)<={41,42}
