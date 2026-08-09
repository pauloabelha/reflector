"""Conditional visual route fields from sparse action-correlated motion."""
from __future__ import annotations
from collections import Counter,deque
from dataclasses import dataclass
from typing import Sequence

class ConditionalRouteError(ValueError):pass
Point=tuple[int,int]
@dataclass(frozen=True)
class RouteField:
 step:int; actor_size:tuple[int,int]; actor_colors:tuple[int,...]; start:Point; current:Point; target:Point; background:int; route_color:int; bounds:tuple[int,int,int,int]; nodes:frozenset[Point]

def _grid(g):
 r=tuple(tuple(map(int,row)) for row in g)
 if not r or not r[0] or any(len(x)!=len(r[0]) for x in r):raise ConditionalRouteError("grid must be rectangular")
 return r

def infer_route_field(initial:Sequence[Sequence[int]],*,before_anchor:Point,after_anchor:Point,size:tuple[int,int],actor_colors:Sequence[int])->RouteField:
 g=_grid(initial);dx=after_anchor[0]-before_anchor[0];dy=after_anchor[1]-before_anchor[1]
 if bool(dx)==bool(dy):raise ConditionalRouteError("motion must establish one cardinal macro axis")
 step=abs(dx or dy);w,h=size
 if step<=max(w,h):raise ConditionalRouteError("macro displacement must exceed actor extent")
 bg=Counter(v for row in g[:-1] for v in row).most_common(1)[0][0]
 pts=[(x,y) for y,row in enumerate(g[:-1]) for x,v in enumerate(row) if v!=bg]
 if not pts:raise ConditionalRouteError("no visual field")
 bounds=min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)
 sx=0 if dx==0 else (1 if dx>0 else -1);sy=0 if dy==0 else (1 if dy>0 else -1)
 lead=before_anchor[0]+sx*w,before_anchor[1]+sy*h;route=g[lead[1]][lead[0]]
 actor=set(map(int,actor_colors)); counts=Counter(g[y][x] for x,y in pts if g[y][x] not in actor and g[y][x] not in {bg,route})
 candidates=[]
 for color,total in counts.items():
  pixels={(x,y) for x,y in pts if g[y][x]==color};seen=set()
  for p in pixels:
   if p in seen:continue
   q=[p];seen.add(p);cc=[]
   while q:
    u=q.pop();cc.append(u)
    for v in ((u[0]+1,u[1]),(u[0]-1,u[1]),(u[0],u[1]+1),(u[0],u[1]-1)):
     if v in pixels and v not in seen:seen.add(v);q.append(v)
   box=min(x for x,y in cc),min(y for x,y in cc),max(x for x,y in cc),max(y for x,y in cc)
   if len(cc)==w*h and (box[2]-box[0]+1,box[3]-box[1]+1)==(w,h):candidates.append((total,color,(box[0],box[1])))
 if not candidates:raise ConditionalRouteError("no actor-sized terminal marker")
 _total,_color,target=min(candidates)
 ox,oy=before_anchor[0]%step,before_anchor[1]%step;x0,y0,x1,y1=bounds
 nodes={(x,y) for y in range(oy,y1+1,step) for x in range(ox,x1+1,step) if x0<=x<=x1 and y0<=y<=y1}
 nodes|={before_anchor,after_anchor,target}
 return RouteField(step,(w,h),tuple(sorted(actor)),before_anchor,after_anchor,target,bg,route,bounds,frozenset(nodes))

def neighbors(field:RouteField,node:Point):
 half=field.step//2;gaps=((0,-field.step,0,-half),(0,field.step,0,half),(-field.step,0,-half,0),(field.step,0,half,0))
 # This function is completed by shortest_route, which receives the immutable
 # visual grid so topology never depends on hidden state.
 return gaps

def shortest_route(field:RouteField,grid:Sequence[Sequence[int]],start:Point|None=None)->tuple[Point,...]:
 g=_grid(grid);origin=field.current if start is None else start;half=field.step//2
 directions=((0,-field.step,0,-half),(0,field.step,0,half),(-field.step,0,-half,0),(field.step,0,half,0))
 q=deque([origin]);parent={origin:None}
 while q:
  u=q.popleft()
  for dx,dy,lx,ly in directions:
   v=u[0]+dx,u[1]+dy;lead=u[0]+lx,u[1]+ly
   if v not in field.nodes or v in parent:continue
   if not(0<=lead[1]<len(g) and 0<=lead[0]<len(g[0]) and g[lead[1]][lead[0]]==field.route_color):continue
   parent[v]=u;q.append(v)
 if field.target not in parent:raise ConditionalRouteError("terminal is unreachable in the visual route field")
 path=[];u=field.target
 while parent[u] is not None:path.append(u);u=parent[u]
 path.reverse();return tuple(path)

def desired_delta(current:Point,path:Sequence[Point])->Point:
 if not path:raise ConditionalRouteError("route is empty")
 return path[0][0]-current[0],path[0][1]-current[1]

def controlled_anchor(grid:Sequence[Sequence[int]],*,colors:Sequence[int],mass:int,size:tuple[int,int])->Point:
 g=_grid(grid);wanted=set(map(int,colors));pixels={(x,y) for y,row in enumerate(g[:-1]) for x,v in enumerate(row) if v in wanted};seen=set();matches=[]
 for p in pixels:
  if p in seen:continue
  q=[p];seen.add(p);cc=[]
  while q:
   u=q.pop();cc.append(u)
   for v in ((u[0]+1,u[1]),(u[0]-1,u[1]),(u[0],u[1]+1),(u[0],u[1]-1)):
    if v in pixels and v not in seen:seen.add(v);q.append(v)
  box=min(x for x,y in cc),min(y for x,y in cc),max(x for x,y in cc),max(y for x,y in cc)
  if len(cc)==mass and (box[2]-box[0]+1,box[3]-box[1]+1)==size:matches.append((box[0],box[1]))
 if len(matches)!=1:raise ConditionalRouteError("controlled appearance is not uniquely grounded")
 return matches[0]
