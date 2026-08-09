from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
import sys
P=Path(__file__).with_name("conditional_route.py");Q=spec_from_file_location("conditional_route_test",P);R=module_from_spec(Q);sys.modules[Q.name]=R;Q.loader.exec_module(R)
def test_sparse_motion_reveals_route_and_terminal():
 g=[[5]*19 for _ in range(19)]
 # Nodes are six pixels apart; route evidence sits halfway between nodes.
 for x,y in ((6,3),(9,6),(9,12),(12,15)):g[y][x]=2
 for y in range(3):
  for x in range(3):g[3+y][3+x]=9
 for y in range(3):
  for x in range(3):g[15+y][15+x]=14
 f=R.infer_route_field(g,before_anchor=(3,3),after_anchor=(9,3),size=(3,3),actor_colors=(9,))
 assert f.target==(15,15) and f.route_color==2
 assert R.shortest_route(f,g)==((9,9),(9,15),(15,15)) or R.shortest_route(f,g)==((9,3),(9,9),(9,15),(15,15))
 assert R.controlled_anchor(g,colors=(9,),mass=9,size=(3,3))==(3,3)
