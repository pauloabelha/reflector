"""Source-blind synthesis of grounded, falsifiable progress hypotheses.

The transferable candidate contains only a small compositional AST.  Concrete
coordinates, palette values, and object IDs remain in its situated binding.
Attention is structural; empirical support begins at zero and can change only
through observed transitions.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, replace
import hashlib
import json
from itertools import combinations
from typing import Any, Mapping, Sequence

Grid = tuple[tuple[int, ...], ...]
Point = tuple[int, int]
PROTOCOL = "autonomous-progress-synthesis-v0"
MAX_REGIONS = 96
MAX_CANDIDATES = 64


class SynthesisError(ValueError):
    pass


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Region:
    region_id: str
    x: int
    y: int
    width: int
    height: int
    cells: frozenset[Point]
    value: int

    @property
    def normalized(self) -> frozenset[Point]:
        return frozenset((x - self.x, y - self.y) for x, y in self.cells)

    @property
    def area(self) -> int:
        return len(self.cells)

    @property
    def solid(self) -> bool:
        return self.area == self.width * self.height

    @property
    def holes(self) -> frozenset[Point]:
        occupied = self.normalized
        return frozenset((x, y) for y in range(self.height) for x in range(self.width) if (x, y) not in occupied)


@dataclass(frozen=True)
class Scene:
    width: int
    height: int
    background_values: tuple[int, ...]
    regions: tuple[Region, ...]


@dataclass(frozen=True)
class GoalCandidate:
    candidate_id: str
    binding_id: str
    ast: Mapping[str, Any]
    binding: Mapping[str, Any]
    attention: int
    support: int = 0
    evidence_count: int = 0


@dataclass(frozen=True)
class PotentialObservation:
    candidate_id: str
    binding_id: str
    before: int
    after: int
    direct: bool
    evidence_id: str


def _grid(raw: Sequence[Sequence[int]]) -> Grid:
    grid = tuple(tuple(int(value) for value in row) for row in raw)
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise SynthesisError("observation must be a rectangular grid")
    return grid


def _coarsen_lattice(grid: Grid) -> Grid:
    height,width=len(grid),len(grid[0]);candidates=[]
    for factor in range(2,9):
        if height%factor or width%factor:continue
        represented=total=0
        for top in range(0,height,factor):
            for left in range(0,width,factor):
                counts=Counter(grid[y][x] for y in range(top,top+factor) for x in range(left,left+factor))
                represented+=max(counts.values());total+=factor*factor
        if represented/total>=0.97:candidates.append(factor)
    factor=max(candidates,default=1)
    if factor==1:return grid
    out=[]
    for top in range(0,height,factor):
        row=[]
        for left in range(0,width,factor):
            counts=Counter(grid[y][x] for y in range(top,top+factor) for x in range(left,left+factor))
            row.append(min(counts,key=lambda value:(-counts[value],value)))
        out.append(tuple(row))
    return tuple(out)


def perceive(raw: Sequence[Sequence[int]]) -> Scene:
    grid = _coarsen_lattice(_grid(raw)); height, width = len(grid), len(grid[0])
    ranked=Counter(value for row in grid for value in row).most_common();backgrounds={ranked[0][0]}
    # A second overwhelmingly common value is usually substrate/interior, not
    # an independently manipulable object. This is a frequency relation, never
    # a palette convention.
    if len(ranked)>2 and ranked[1][1]>=3*ranked[2][1]:backgrounds.add(ranked[1][0])
    remaining = {(x, y) for y, row in enumerate(grid) for x, value in enumerate(row) if value not in backgrounds}
    regions = []
    while remaining:
        seed = min(remaining, key=lambda point: (point[1], point[0])); value = grid[seed[1]][seed[0]]
        remaining.remove(seed); queue = deque([seed]); cells = {seed}
        while queue:
            x, y = queue.popleft()
            for point in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if point in remaining and grid[point[1]][point[0]]==value:
                    remaining.remove(point); cells.add(point); queue.append(point)
        xs, ys = zip(*cells); x0, y0 = min(xs), min(ys); w, h = max(xs)-x0+1, max(ys)-y0+1
        identity = {"bbox": [x0,y0,w,h], "mask": sorted((x-x0,y-y0) for x,y in cells)}
        regions.append(Region("region:"+stable_hash(identity)[:20],x0,y0,w,h,frozenset(cells),value))
    # A multichromatic object is represented both by its palette components and
    # by a compound occupancy region when smaller components fill holes inside
    # an enclosing mask. Adjacent objects are never merged merely by contact.
    compounds=[]
    for outer in tuple(regions):
        enclosed={point for region in regions if region is not outer for point in region.cells if outer.x<=point[0]<outer.x+outer.width and outer.y<=point[1]<outer.y+outer.height}
        combined=set(outer.cells)|enclosed
        if enclosed and combined!=set(outer.cells):
            identity={"bbox":[outer.x,outer.y,outer.width,outer.height],"mask":sorted((x-outer.x,y-outer.y) for x,y in combined)}
            compounds.append(Region("region:"+stable_hash(identity)[:20],outer.x,outer.y,outer.width,outer.height,frozenset(combined),outer.value))
    regions.extend(compounds)
    if len(regions) > MAX_REGIONS:
        raise SynthesisError("region population exceeds bounded grammar")
    return Scene(width,height,tuple(sorted(backgrounds)),tuple(sorted(regions,key=lambda r:(r.y,r.x,r.height,r.width,r.region_id))))


def cross_controllers(raw:Sequence[Sequence[int]])->tuple[dict[str,Any],...]:
    grid=_coarsen_lattice(_grid(raw));height,width=len(grid),len(grid[0]);backgrounds=set(perceive(grid).background_values);rows=[]
    for y in range(2,height-2):
        for x in range(2,width-2):
            neighbors=(grid[y-1][x],grid[y+1][x],grid[y][x-1],grid[y][x+1])
            if len(set(neighbors))!=1 or neighbors[0] in backgrounds:continue
            value=neighbors[0];left=x-1
            while left-1>=0 and grid[y][left-1]==value:left-=1
            right=x+1
            while right+1<width and grid[y][right+1]==value:right+=1
            top=y-1
            while top-1>=0 and grid[top-1][x]==value:top-=1
            bottom=y+1
            while bottom+1<height and grid[bottom+1][x]==value:bottom+=1
            if min(x-left,right-x,y-top,bottom-y)<2:continue
            mask=frozenset({(xx-left,y-top) for xx in range(left,right+1) if grid[y][xx]==value}|{(x-left,yy-top) for yy in range(top,bottom+1) if grid[yy][x]==value})
            body={"x":left,"y":top,"width":right-left+1,"height":bottom-top+1,"mask":[list(p) for p in sorted(mask)],"class":value,"active":grid[y][x]!=value}
            body["controller_id"]="controller:"+stable_hash({k:v for k,v in body.items() if k!="active"})[:20];rows.append(body)
    unique={row["controller_id"]:row for row in rows}
    return tuple(sorted(unique.values(),key=lambda row:(not row["active"],row["y"],row["x"],row["controller_id"])))


def framed_requirements(raw:Sequence[Sequence[int]])->tuple[dict[str,Any],...]:
    grid=_coarsen_lattice(_grid(raw));height,width=len(grid),len(grid[0]);backgrounds=set(perceive(grid).background_values);rows=[]
    for y in range(1,height-1):
        for x in range(1,width-1):
            ring=[grid[yy][xx] for yy in range(y-1,y+2) for xx in range(x-1,x+2) if (xx,yy)!=(x,y)]
            if len(set(ring))==1 and ring[0] not in backgrounds and grid[y][x]!=ring[0] and grid[y][x] not in backgrounds:
                rows.append({"point":[x,y],"class":grid[y][x]})
    return tuple(rows)


def _candidate(kind: str, roles: Mapping[str, Any], binding: Mapping[str, Any], attention: int) -> GoalCandidate:
    ast = {
        "protocol": PROTOCOL,
        "type": "GoalPotential",
        "roles": dict(roles),
        "potential": {"type": kind, "direction": "minimize", "lower_bound": 0},
        "terminal": {"type": "EqualsLowerBound"},
    }
    cid = "goal:" + stable_hash(ast)[:24]
    bid = "grounding:" + stable_hash({"candidate_id":cid,"binding":binding})[:24]
    return GoalCandidate(cid, bid, ast, dict(binding), max(0,min(100,int(attention))))


def synthesize(raw: Sequence[Sequence[int]]) -> tuple[GoalCandidate, ...]:
    """Enumerate bounded compositions; no game/family selector is consulted."""
    scene = perceive(raw); candidates = []
    useful = [region for region in scene.regions if region.area >= 2 and region.width < scene.width and region.height < scene.height]

    # Sets arise from perceptual equivalence; containers arise independently
    # from interior capacity.  Every compatible cross-product is proposed.
    shape_classes: dict[tuple[int,int,frozenset[Point]], list[Region]] = {}
    for region in useful:
        shape_classes.setdefault((region.width,region.height,region.normalized),[]).append(region)
    solid_sets = [group for group in shape_classes.values() if len(group)>=2 and all(r.solid for r in group)]
    open_regions = [region for region in useful if region.holes and region.area >= 3]
    for members in solid_sets:
        compatible=[container for container in open_regions if all((container.width-2,container.height-2)==(member.width,member.height) for member in members)]
        if len(compatible)>=len(members):
                candidates.append(_candidate(
                    "UnassignedMemberCount",
                    {"members":{"type":"EquivalenceClass"},"containers":{"type":"CapacityCompatibleSet"}},
                    {"members":[r.region_id for r in members],"containers":[r.region_id for r in compatible]},
                    70 + min(20,5*len(members)),
                ))

    # Pairwise target matching is generated for similarly scaled regions; no
    # claim is made that either member is the target until actions provide it.
    for left, right in combinations(useful,2):
        ratio = max(left.width/right.width,right.width/left.width,left.height/right.height,right.height/left.height)
        if ratio <= 1.5:
            candidates.append(_candidate(
                "NormalizedMaskMismatch",
                {"candidate":{"type":"Transformable"},"reference":{"type":"PersistentRegion"}},
                {"candidate":left.region_id,"reference":right.region_id},
                25 + (15 if left.normalized != right.normalized else 0),
            ))

    # Boundary emitters, repeated open terminals and an intervening bar compose
    # a coverage hypothesis.  These roles are geometric, palette-independent.
    top = [r for r in scene.regions if r.y <= 1 and r.width <= 2 and r.height <= 2]
    bottom_open = [r for r in open_regions if r.y+r.height >= scene.height-2]
    terminal_classes: dict[tuple[int,int,frozenset[Point]],list[Region]] = {}
    for region in bottom_open:
        terminal_classes.setdefault((region.width,region.height,region.normalized),[]).append(region)
    bars = [r for r in useful if r.height==1 and r.width>=3 and 1<r.y<scene.height-2]
    earliest_by_column={}
    for region in top:
        earliest_by_column[region.x]=min(region,earliest_by_column.get(region.x,region),key=lambda r:(r.y,r.region_id))
    for source in earliest_by_column.values():
        for terminals in terminal_classes.values():
            if len(terminals)<2: continue
            for transducer in bars:
                candidates.append(_candidate(
                    "UnservedTerminalCount",
                    {"source":{"type":"BoundaryEmitter"},"terminals":{"type":"RepeatedOpenRegions"},"transducer":{"type":"Transformable"}},
                    {"source":source.region_id,"terminals":[r.region_id for r in terminals],"transducer":transducer.region_id},
                    75 + min(20,5*len(terminals)),
                ))

    controllers=cross_controllers(raw);requirements=framed_requirements(raw);assignments=[]
    for controller in controllers:
        points=[row["point"] for row in requirements if row["class"]==controller["class"]]
        if len(points)>=2:assignments.append({"controller":controller,"requirements":points})
    if assignments and len(assignments)==len(controllers):
        candidates.append(_candidate(
            "UncoveredRequirementCount",
            {"controllers":{"type":"TransformableSet"},"requirements":{"type":"SparseSpecificationLayer"}},
            {"assignments":assignments},
            80+min(15,sum(len(row["requirements"]) for row in assignments)),
        ))

    unique: dict[tuple[str,str],GoalCandidate] = {}
    for candidate in candidates:
        key = candidate.candidate_id, stable_hash(candidate.binding)
        unique[key] = candidate
    ranked = sorted(unique.values(),key=lambda c:(-c.attention,c.candidate_id,stable_hash(c.binding)))
    return tuple(ranked[:MAX_CANDIDATES])


def evaluate(candidate: GoalCandidate, raw: Sequence[Sequence[int]]) -> int | None:
    """Evaluate only directly observable potentials; unknown stays unknown."""
    scene = perceive(raw); regions = {region.region_id:region for region in scene.regions}
    kind = candidate.ast["potential"]["type"]; binding = candidate.binding
    try:
        if kind == "UnassignedMemberCount":
            containers=[regions[cid] for cid in binding["containers"]]
            return sum(not any(container.x < regions[mid].x and container.y < regions[mid].y and regions[mid].x+regions[mid].width < container.x+container.width and regions[mid].y+regions[mid].height < container.y+container.height for container in containers) for mid in binding["members"])
        if kind == "NormalizedMaskMismatch":
            left,right=regions[binding["candidate"]],regions[binding["reference"]]
            scale=max(left.width,right.width,left.height,right.height)
            def sample(region):
                return {(round(x*(scale-1)/max(1,region.width-1)),round(y*(scale-1)/max(1,region.height-1))) for x,y in region.normalized}
            return len(sample(left)^sample(right))
        if kind == "UnservedTerminalCount":
            source=regions[binding["source"]];bar=regions[binding["transducer"]]
            terminals=[regions[rid] for rid in binding["terminals"]]
            if not bar.x <= source.x < bar.x+bar.width:return len(terminals)
            exits={bar.x-1,bar.x+bar.width}
            ports=[]
            for terminal in terminals:
                top_cells={x for x,y in terminal.cells if y==terminal.y}
                gaps=[x for x in range(terminal.x,terminal.x+terminal.width) if x not in top_cells]
                if len(gaps)!=1:return None
                ports.append(gaps[0])
            return sum(port not in exits for port in ports)
        if kind == "UncoveredRequirementCount":
            current=cross_controllers(raw);by_class={row["class"]:row for row in current};uncovered=0
            for assignment in binding["assignments"]:
                spec=assignment["controller"];controller=by_class.get(spec["class"])
                if controller is None:return None
                cells={(controller["x"]+dx,controller["y"]+dy) for dx,dy in map(tuple,controller["mask"])}
                uncovered+=sum(tuple(point) not in cells for point in assignment["requirements"])
            return uncovered
    except KeyError:
        return None
    return None


def adjudicate(candidate: GoalCandidate, observation: PotentialObservation) -> GoalCandidate:
    if observation.candidate_id != candidate.candidate_id or observation.binding_id != candidate.binding_id:
        raise SynthesisError("evidence targets another goal")
    if not observation.direct:
        return candidate
    delta = observation.before-observation.after
    # Controllability raises attention. Repeated directionally useful evidence
    # raises support, but structure alone never does.
    attention = candidate.attention + (8 if delta else 1)
    support = candidate.support + (10 if delta>0 else -3 if delta<0 else 0)
    return replace(candidate,attention=max(0,min(100,attention)),support=max(-100,min(100,support)),evidence_count=candidate.evidence_count+1)


def choose_focus(candidates: Sequence[GoalCandidate]) -> GoalCandidate | None:
    viable=[candidate for candidate in candidates if candidate.support>=0]
    return min(viable,key=lambda c:(-c.support,-c.attention,c.candidate_id),default=None)


def infer_role_translation(candidate:GoalCandidate,before_raw:Sequence[Sequence[int]],after_raw:Sequence[Sequence[int]])->Point|None:
    """Infer an opaque intervention's translation on any grounded role."""
    if candidate.ast["potential"]["type"]=="UncoveredRequirementCount":
        before_controllers={row["class"]:row for row in cross_controllers(before_raw)}
        after_controllers={row["class"]:row for row in cross_controllers(after_raw)}
        deltas=[]
        for assignment in candidate.binding["assignments"]:
            class_id=assignment["controller"]["class"]
            source,target=before_controllers.get(class_id),after_controllers.get(class_id)
            if source is None or target is None:continue
            delta=(target["x"]-source["x"],target["y"]-source["y"])
            if delta!=(0,0):deltas.append(delta)
        if deltas:
            counts=Counter(deltas)
            return min(counts,key=lambda delta:(-counts[delta],abs(delta[0])+abs(delta[1]),delta))
    before=perceive(before_raw);after=perceive(after_raw);before_by_id={r.region_id:r for r in before.regions}
    role_ids=[]
    def collect(value):
        if isinstance(value,str) and value.startswith("region:"):role_ids.append(value)
        elif isinstance(value,Mapping):
            for item in value.values():collect(item)
        elif isinstance(value,(list,tuple)):
            for item in value:collect(item)
    collect(candidate.binding)
    deltas=[]
    for rid in role_ids:
        source=before_by_id.get(rid)
        if source is None:continue
        matches=[r for r in after.regions if (r.width,r.height,r.normalized)==(source.width,source.height,source.normalized)]
        if not matches:continue
        target=min(matches,key=lambda r:(abs(r.x-source.x)+abs(r.y-source.y),r.y,r.x,r.region_id))
        delta=(target.x-source.x,target.y-source.y)
        if delta!=(0,0):deltas.append(delta)
    if not deltas:return None
    counts=Counter(deltas);return min(counts,key=lambda delta:(-counts[delta],abs(delta[0])+abs(delta[1]),delta))


def public_document(candidate: GoalCandidate) -> dict[str,Any]:
    """Transferable workspace write: bindings are deliberately excluded."""
    return {"kind":"goal_potential","identity":{"candidate_id":candidate.candidate_id},"payload":{"protocol":PROTOCOL,"ast":candidate.ast,"attention":candidate.attention,"empirical_support":candidate.support,"evidence_count":candidate.evidence_count,"authority":"environment-evidence-only"}}
