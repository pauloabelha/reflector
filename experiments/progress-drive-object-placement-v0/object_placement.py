"""Visual multi-object placement with opaque selection and motion actions."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from itertools import permutations
from typing import Mapping,Sequence

Point=tuple[int,int];Grid=tuple[tuple[int,...],...]
class PlacementError(ValueError):pass
class NoPlacementPlan(RuntimeError):pass
@dataclass(frozen=True)
class Box:
 x:int;y:int;width:int;height:int
@dataclass(frozen=True)
class PlacementScene:
 items:tuple[Box,...];slots:tuple[Box,...];blocked:frozenset[Point];bounds:Box
@dataclass(frozen=True)
class PlacementStep:
 kind:str;item:int;before:Point;after:Point;action_id:int;data:tuple[tuple[str,int],...]=()
@dataclass(frozen=True)
class PlacementPlan:
 steps:tuple[PlacementStep,...]
 @property
 def actions(self):return tuple((s.action_id,dict(s.data)) for s in self.steps)

def _grid(raw:Sequence[Sequence[int]])->Grid:
 g=tuple(tuple(map(int,row)) for row in raw)
 if not g or not g[0] or any(len(r)!=len(g[0]) for r in g):raise PlacementError("grid must be rectangular")
 return g
def _components(points:set[Point]):
 out=[]
 while points:
  seed=points.pop();cc={seed};q=[seed]
  while q:
   x,y=q.pop()
   for v in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if v in points:points.remove(v);cc.add(v);q.append(v)
  out.append(cc)
 return out
def _box(cc:set[Point])->Box:
 xs=[x for x,y in cc];ys=[y for x,y in cc];return Box(min(xs),min(ys),max(xs)-min(xs)+1,max(ys)-min(ys)+1)

def infer_scene(raw:Sequence[Sequence[int]])->PlacementScene:
 """Infer filled movable objects, hollow compatible slots, and solid obstacles."""
 g=_grid(raw);h,w=len(g),len(g[0]);from collections import Counter
 counts=Counter(v for row in g for v in row);ranked_counts=counts.most_common()
 backgrounds={ranked_counts[0][0]}
 if len(ranked_counts)>2 and ranked_counts[1][1]>=3*ranked_counts[2][1]:backgrounds.add(ranked_counts[1][0])
 foreground={(x,y) for y,row in enumerate(g) for x,v in enumerate(row) if v not in backgrounds}
 components=_components(foreground);slots=[];items=[];obstacles=[]
 for cc in components:
  b=_box(cc)
  if b.width<3 or b.height<3:continue
  border={(x,y) for y in range(b.y,b.y+b.height) for x in range(b.x,b.x+b.width) if x in {b.x,b.x+b.width-1} or y in {b.y,b.y+b.height-1}}
  interior={(x,y) for y in range(b.y+1,b.y+b.height-1) for x in range(b.x+1,b.x+b.width-1)}
  if border<=cc and not (interior&cc):slots.append(b)
  elif len(cc)>=b.width*b.height:items.append(b)
  else:obstacles.append(cc)
 # Multicolor filled items are connected but not necessarily every cell belongs to
 # one value; foreground occupancy, not chroma, defines solidity.
 compatible_items=[]
 for b in items:
  if any((slot.width-2,slot.height-2)==(b.width,b.height) for slot in slots):compatible_items.append(b)
  else:obstacles.append({(x,y) for y in range(b.y,b.y+b.height) for x in range(b.x,b.x+b.width)})
 if not compatible_items or len(compatible_items)!=len(slots):raise PlacementError("no balanced filled-object/hollow-slot population")
 blocked=frozenset(p for cc in obstacles for p in cc)
 return PlacementScene(tuple(sorted(compatible_items,key=lambda b:(b.y,b.x))),tuple(sorted(slots,key=lambda b:(b.y,b.x))),blocked,Box(0,0,w,h))

def _path(start:Point,target:Point,size:tuple[int,int],blocked:set[Point],bounds:Box,step:int):
 iw,ih=size
 def valid(p):
  x,y=p
  if x<bounds.x or y<bounds.y or x+iw>bounds.x+bounds.width or y+ih>bounds.y+bounds.height:return False
  return not any((px,py) in blocked for py in range(y,y+ih) for px in range(x,x+iw))
 q=deque([start]);parent={start:None}
 while q:
  u=q.popleft()
  if u==target:break
  for v in ((u[0],u[1]-step),(u[0],u[1]+step),(u[0]-step,u[1]),(u[0]+step,u[1])):
   if v not in parent and valid(v):parent[v]=u;q.append(v)
 if target not in parent:raise NoPlacementPlan(f"slot {target} unreachable from {start}")
 out=[];u=target
 while parent[u] is not None:out.append(u);u=parent[u]
 return tuple(reversed(out))

def plan_placement(scene:PlacementScene,delta_actions:Mapping[Point,int],*,select_action_id:int)->PlacementPlan:
 if not delta_actions:raise PlacementError("motion calibration is required")
 stepsizes={abs(dx or dy) for dx,dy in delta_actions if bool(dx)!=bool(dy)}
 if len(stepsizes)!=1:raise PlacementError("one cardinal step size is required")
 step=next(iter(stepsizes));best=None
 for assignment in permutations(range(len(scene.slots))):
  blocked=set(scene.blocked);positions=[(b.x,b.y) for b in scene.items];candidate=[]
  try:
   for item_index,slot_index in enumerate(assignment):
    item=scene.items[item_index];target_slot=scene.slots[slot_index];target=(target_slot.x+1,target_slot.y+1)
    other={(x,y) for j,b in enumerate(scene.items) if j!=item_index for y in range(positions[j][1],positions[j][1]+b.height) for x in range(positions[j][0],positions[j][0]+b.width)}
    path=_path(positions[item_index],target,(item.width,item.height),blocked|other,scene.bounds,step)
    centre=(positions[item_index][0]+item.width//2,positions[item_index][1]+item.height//2)
    candidate.append(PlacementStep("select",item_index,positions[item_index],positions[item_index],select_action_id,(("x",centre[0]),("y",centre[1]))))
    current=positions[item_index]
    for nxt in path:
     delta=nxt[0]-current[0],nxt[1]-current[1]
     if delta not in delta_actions:raise NoPlacementPlan("path requires an uncalibrated motion")
     candidate.append(PlacementStep("move",item_index,current,nxt,int(delta_actions[delta])));current=nxt
    positions[item_index]=current
  except NoPlacementPlan:continue
  key=(len(candidate),tuple((s.action_id,s.data) for s in candidate))
  if best is None or key<best[0]:best=(key,tuple(candidate))
 if best is None:raise NoPlacementPlan("no complete compatible assignment")
 return PlacementPlan(best[1])
