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

@dataclass(frozen=True)
class PushAssistance:
 pusher_index:int;blocked_item_index:int;direction:Point;steps:tuple[PlacementStep,...]

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

def track_item_scene(initial_raw:Sequence[Sequence[int]],current_raw:Sequence[Sequence[int]],scene:PlacementScene)->PlacementScene:
 """Preserve filled-item identities when contact merges connected components."""
 initial=_grid(initial_raw);current=_grid(current_raw);found=[]
 signatures=[]
 for item in scene.items:
  perimeter=tuple(initial[y][x] for y in range(item.y,item.y+item.height) for x in range(item.x,item.x+item.width) if x in {item.x,item.x+item.width-1} or y in {item.y,item.y+item.height-1})
  signatures.append(((item.width,item.height),perimeter))
 for (iw,ih),signature in sorted(set(signatures)):
  for y in range(0,len(current)-ih+1):
   for x in range(0,len(current[0])-iw+1):
    candidate=tuple(current[yy][xx] for yy in range(y,y+ih) for xx in range(x,x+iw) if xx in {x,x+iw-1} or yy in {y,y+ih-1})
    if candidate==signature:
     box=Box(x,y,iw,ih)
     # A preserved object that now occupies a compatible hollow slot is no
     # longer a member of the live unassigned population.  Its pixels remain
     # visible, so correspondence must apply the role predicate rather than
     # counting every matching appearance as an ambiguity.
     assigned=any(
      slot.x < box.x and slot.y < box.y
      and box.x+box.width < slot.x+slot.width
      and box.y+box.height < slot.y+slot.height
      for slot in scene.slots
     )
     if not assigned:found.append(box)
 unique=tuple(sorted(set(found),key=lambda b:(b.y,b.x)))
 if len(unique)!=len(scene.items):raise PlacementError(f"correspondence preserved {len(unique)} of {len(scene.items)} items")
 return PlacementScene(unique,scene.slots,scene.blocked,scene.bounds)

def _path(start:Point,target:Point,size:tuple[int,int],blocked:set[Point],bounds:Box,step:int):
 iw,ih=size
 def valid(p):
  x,y=p
  if x<bounds.x or y<bounds.y or x+iw>bounds.x+bounds.width or y+ih>bounds.y+bounds.height:return False
  return not any((px,py) in blocked for py in range(y,y+ih) for px in range(x,x+iw))
 q=deque([start]);parent={start:None};initial_dx=target[0]-start[0];initial_dy=target[1]-start[1]
 horizontal=((step if initial_dx>=0 else -step,0),(-step if initial_dx>=0 else step,0))
 vertical=((0,step if initial_dy>=0 else -step),(0,-step if initial_dy>=0 else step))
 directions=horizontal+vertical if abs(initial_dx)>abs(initial_dy) else vertical+horizontal
 while q:
  u=q.popleft()
  if u==target:break
  for dx,dy in directions:
   v=(u[0]+dx,u[1]+dy)
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

def plan_blocked_assignment_push(scene:PlacementScene,delta_actions:Mapping[Point,int],*,select_action_id:int)->PushAssistance:
 """Find a generic aligned pusher for an item separated from a slot by a band.

 The returned final movement is a falsifiable prospective push.  Its displacement
 must be observed before the caller replans; this function never fabricates the
 pushed item's successor position.
 """
 if not delta_actions:raise PlacementError("motion calibration is required")
 for blocked_index,blocked_item in enumerate(scene.items):
  compatible=[s for s in scene.slots if (s.width-2,s.height-2)==(blocked_item.width,blocked_item.height)]
  for slot in compatible:
   target=(slot.x+1,slot.y+1);dx=target[0]-blocked_item.x;dy=target[1]-blocked_item.y
   axes=[]
   if dx:axes.append(((1 if dx>0 else -1,0),abs(dx)))
   if dy:axes.append(((0,1 if dy>0 else -1),abs(dy)))
   for direction,_distance in axes:
    sx,sy=direction
    if sx:
     lo,hi=sorted((blocked_item.x,target[0]));separates=any(lo<px<hi and blocked_item.y<=py<blocked_item.y+blocked_item.height for px,py in scene.blocked)
    else:
     lo,hi=sorted((blocked_item.y,target[1]));separates=any(lo<py<hi and blocked_item.x<=px<blocked_item.x+blocked_item.width for px,py in scene.blocked)
    if not separates:continue
    for pusher_index,pusher in enumerate(scene.items):
     if pusher_index==blocked_index or (pusher.width,pusher.height)!=(blocked_item.width,blocked_item.height):continue
     aligned=(pusher.y==blocked_item.y if sx else pusher.x==blocked_item.x)
     behind=(pusher.x<blocked_item.x if sx>0 else pusher.x>blocked_item.x if sx<0 else pusher.y<blocked_item.y if sy>0 else pusher.y>blocked_item.y)
     if not(aligned and behind):continue
     step=abs(sx or sy)*next((abs(x or y) for x,y in delta_actions if (x==0) != (y==0)))
     delta=(sx*step,sy*step)
     if delta not in delta_actions:continue
     gap=(blocked_item.x-(pusher.x+pusher.width) if sx>0 else pusher.x-(blocked_item.x+blocked_item.width) if sx<0 else blocked_item.y-(pusher.y+pusher.height) if sy>0 else pusher.y-(blocked_item.y+blocked_item.height))
     if gap<0 or gap%step:continue
     centre=(pusher.x+pusher.width//2,pusher.y+pusher.height//2);steps=[PlacementStep("select-pusher",pusher_index,(pusher.x,pusher.y),(pusher.x,pusher.y),select_action_id,(("x",centre[0]),("y",centre[1])))]
     current=(pusher.x,pusher.y)
     for _ in range(gap//step+1):
      nxt=(current[0]+delta[0],current[1]+delta[1]);steps.append(PlacementStep("prospective-push",pusher_index,current,nxt,delta_actions[delta]));current=nxt
     return PushAssistance(pusher_index,blocked_index,direction,tuple(steps))
 raise NoPlacementPlan("no aligned pusher resolves a blocked assignment")
