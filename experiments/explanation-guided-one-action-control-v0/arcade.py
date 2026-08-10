"""Live and replay browser arcade for the explanation-guided agent."""

from __future__ import annotations

import json
from pathlib import Path
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Sequence
from urllib.parse import parse_qs, urlparse


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _grid(value: Any) -> list[list[int]]:
    while isinstance(value, list) and value and isinstance(value[0], list) and value[0] and isinstance(value[0][0], list):
        value = value[-1]
    return [[int(cell) for cell in row] for row in value] if isinstance(value, list) else []


class ReplayStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _run(self, run_id: str) -> Path:
        if not run_id or Path(run_id).name != run_id:
            raise ValueError("invalid run id")
        path = (self.root / run_id).resolve()
        if path.parent != self.root or not path.is_dir():
            raise ValueError("unknown run")
        return path

    def runs(self) -> list[dict[str, Any]]:
        output = []
        if not self.root.is_dir():
            return output
        for path in sorted(self.root.glob("run-*"), reverse=True):
            manifest = _read_json(path / "manifest.json", {}) or {}
            result_files = sorted((path / "results").glob("*.json")) if (path / "results").is_dir() else []
            result = _read_json(result_files[0], {}) if result_files else {}
            workspaces = sorted((path / "workspaces").glob("*")) if (path / "workspaces").is_dir() else []
            start = None
            if workspaces:
                events = sorted((workspaces[0] / "events").glob("*.json"))
                start = next((_read_json(item, {}) for item in events if _read_json(item, {}).get("event_type") == "WorkspaceStarted"), None)
            output.append({
                "run_id": path.name,
                "game": result.get("game") or (start or {}).get("payload", {}).get("game"),
                "level": int(manifest.get("config", {}).get("start_level", 1)),
                "status": "complete" if result else "partial",
                "actions": int(result.get("actions", 0)),
                "levels_completed": int(result.get("levels_completed", 0)),
                "r2_version": manifest.get("experiment"),
                "protocol": manifest.get("protocol"),
                "manifest_digest": manifest.get("manifest_digest"),
                "created_at": path.stat().st_mtime,
            })
        return output

    def replay(self, run_id: str) -> dict[str, Any]:
        run = self._run(run_id)
        manifest = _read_json(run / "manifest.json", {}) or {}
        workspaces = sorted((run / "workspaces").glob("*"))
        if not workspaces:
            raise ValueError("run has no workspace")
        workspace = workspaces[0]
        events = [_read_json(path, {}) for path in sorted((workspace / "events").glob("*.json"))]
        blobs = workspace / "blobs" / "sha256"

        def blob(digest: Any) -> Any:
            return _read_json(blobs / f"{digest}.json", {})

        initial = next((item for item in events if item.get("event_type") == "InitialObservation"), None)
        if initial is None:
            raise ValueError("run has no initial observation")
        first = blob(initial["payload"]["observation_blob"])
        timeline: list[dict[str, Any]] = [{
            "turn": 0, "frame": _grid(first.get("grid", [])), "decision": None,
            "scratchpad": None, "settlement": None,
        }]
        scratchpad = None
        pending_decision = None
        for event in events:
            kind = event.get("event_type")
            payload = event.get("payload", {})
            if kind == "QwenTaskCompleted":
                compilation = blob(payload.get("compilation_blob"))
                if isinstance(compilation.get("working_note"), dict):
                    scratchpad = compilation["working_note"]
                    timeline[-1]["scratchpad"] = scratchpad
            elif kind == "ActionDecision":
                document = blob(payload.get("decision_blob"))
                pending_decision = document.get("controller", {}).get("decision_contract")
                timeline[-1]["decision"] = pending_decision
            elif kind == "TransitionCommitted":
                after = blob(payload.get("after_blob"))
                record = after.get("record", {})
                settlement = {
                    "action": int(payload.get("action_id", -1)),
                    "observation_changed": payload.get("before_digest") != payload.get("after_digest"),
                    "levels_completed": int(payload.get("levels_completed", 0)),
                    "prospective_judgments": payload.get("prospective_judgments", []),
                }
                timeline.append({
                    "turn": len(timeline), "frame": _grid(after.get("grid", [])),
                    "decision": None, "executed_decision": pending_decision,
                    "scratchpad": scratchpad, "settlement": settlement,
                    "levels_completed": int(record.get("levels_completed", payload.get("levels_completed", 0))),
                })
                pending_decision = None
        result_files = sorted((run / "results").glob("*.json")) if (run / "results").is_dir() else []
        result = _read_json(result_files[0], {}) if result_files else {}
        return {
            "run_id": run_id,
            "metadata": {
                "r2_version": manifest.get("experiment"),
                "protocol": manifest.get("protocol"),
                "manifest_digest": manifest.get("manifest_digest"),
                "source_hashes": manifest.get("sources", {}),
                "game": result.get("game"),
                "start_level": manifest.get("config", {}).get("start_level", 1),
                "actions": len(timeline) - 1,
                "levels_completed": result.get("levels_completed"),
                "replay_verified": result.get("replay_verified"),
                "support_authority_violations": result.get("support_authority_violations"),
            },
            "timeline": timeline,
        }


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Reflector II · Agent Arcade</title>
<style>:root{--ink:#edf3ed;--muted:#84928c;--lime:#c9ff45;--cyan:#4ce4d4;--panel:#111715;--line:#29332f}*{box-sizing:border-box}body{margin:0;background:#080b0a;color:var(--ink);font:14px ui-monospace,SFMono-Regular,monospace}header{display:flex;align-items:end;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:21px;letter-spacing:.08em}small,.muted{color:var(--muted)}main{display:grid;grid-template-columns:minmax(240px,.55fr) minmax(420px,1.2fr) minmax(330px,.75fr);gap:12px;padding:12px;max-width:1800px;margin:auto;height:calc(100dvh - 70px);overflow:hidden}.game-column{display:flex;flex-direction:column;gap:10px;min-height:0}.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}.stack{display:grid;gap:12px;overflow:auto;min-height:0}.scratch-column{overflow:auto;min-height:0}.board-panel{display:flex;flex:1;min-height:0;flex-direction:column}.canvas-wrap{display:grid;place-items:center;flex:1;min-height:160px;overflow:hidden}canvas{display:block;width:auto;height:100%;max-width:100%;max-height:100%;aspect-ratio:1;image-rendering:pixelated;background:#030504;border-radius:6px}.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:7px 0}button,select,input{font:inherit;color:var(--ink);background:#18201d;border:1px solid #3b4943;border-radius:6px;padding:7px}button:hover{color:var(--lime);border-color:var(--lime);cursor:pointer}input[type=range]{flex:1;min-width:180px}h2{font-size:12px;color:var(--cyan);letter-spacing:.12em;margin:0 0 8px}.tag{color:#07100b;background:var(--lime);border-radius:99px;padding:4px 8px;font-weight:bold}.entry{padding:10px 0;border-top:1px solid var(--line)}.key{color:var(--muted)}pre{white-space:pre-wrap;word-break:break-word;margin:0;line-height:1.45}.scratch{border-left:3px solid var(--cyan)}.choice{border-left:3px solid var(--lime)}.qclock{display:flex;align-items:center;gap:12px;padding:10px;margin:4px 0 14px;background:#0b1210;border:1px solid #263b35;border-radius:9px}.ring{--p:0;width:46px;height:46px;flex:0 0 46px;border-radius:50%;background:conic-gradient(var(--cyan) calc(var(--p)*1turn),#23302b 0);display:grid;place-items:center}.ring:after{content:'';width:34px;height:34px;border-radius:50%;background:#0b1210}.clocktext{line-height:1.45}.clockphase{color:var(--cyan)}@media(max-width:1050px){main{grid-template-columns:minmax(210px,.5fr) minmax(400px,1fr);height:calc(100dvh - 70px)}.stack{display:none}}@media(max-width:720px){main{grid-template-columns:1fr;height:auto;overflow:visible}.scratch-column{max-height:35dvh}.canvas-wrap{height:calc(100dvh - 390px);min-height:220px}.stack{display:grid;overflow:visible}}</style></head>
<body><header><div><h1>REFLECTOR II / AGENT ARCADE</h1><small>FRAME 0 EXPLAINS → CHOOSE ONE → OBSERVE → SETTLE</small></div><span id=state class=tag>IDLE</span></header><main><aside class="panel scratch scratch-column"><h2>QWEN SCRATCHPAD · UNVERIFIED</h2><div id=qclock class=qclock><div id=qring class=ring></div><div class=clocktext><div id=qphase class=clockphase>READY</div><small id=qeta>prior ETA 18.0s</small></div></div><div id=scratch></div></aside><section class=game-column><article class=panel><h2>PLAY FROM SCRATCH</h2><div class=bar><label>GAME <select id=game></select></label><label>LEVEL <input id=level type=number min=1 value=1 style="width:70px"></label><button id=start>START AGENT</button></div><h2>PLAYBACK</h2><div class=bar><select id=runs><option>No stored runs</option></select><button id=load>LOAD</button></div></article><article class="panel board-panel"><div class=canvas-wrap><canvas id=board width=800 height=800></canvas></div><div class=bar><button id=pause>PAUSE</button><button id=step>STEP ONE</button><button id=back>←</button><button id=play>PLAY REPLAY</button><button id=forward>→</button><label>SPEED <select id=speed><option value=.25>.25×</option><option value=.5>.5×</option><option value=1 selected>1×</option><option value=2>2×</option><option value=5>5×</option><option value=10>10×</option></select></label></div><div class=bar><input id=scrub type=range min=0 max=0 value=0><span id=turn class=muted></span></div></article></section><section class=stack><article class="panel choice"><h2>EXPLANATION · CURRENT</h2><div id=explanations></div></article><article class=panel style="flex:0 0 auto"><h2>TOP-3 NEXT ACTIONS</h2><div id=decision></div></article><article class=panel><h2>SALIENT SCHEMAS</h2><div id=schemas></div></article><article class=panel><h2>METADATA</h2><div id=metadata></div></article></section></main>
<script>const $=q=>document.querySelector(q),P=['#080b0a','#2774f0','#ef4545','#34c66b','#f4d94c','#929995','#d850c4','#ff942e','#5bdce4','#8e58d8','#f0f3ef','#68a9ff','#ff7d87','#83e3a1','#fff17c','#fff17c','#c8ceca'];let data={},replay=null,index=0,timer=null;const esc=x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;'),pretty=x=>`<pre>${esc(JSON.stringify(x??null,null,2))}</pre>`;async function api(path,body){let r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined}),j=await r.json();if(!r.ok)throw Error(j.error);return j}function draw(f){let c=$('#board'),x=c.getContext('2d');x.fillStyle='#030504';x.fillRect(0,0,c.width,c.height);if(!f?.length)return;let h=f.length,w=f[0].length,z=Math.min(c.width/w,c.height/h),ox=(c.width-w*z)/2,oy=(c.height-h*z)/2;f.forEach((r,y)=>r.forEach((v,i)=>{x.fillStyle=P[v]||'#fff';x.fillRect(ox+i*z,oy+y*z,Math.ceil(z),Math.ceil(z))}))}function render(){draw(data.frame);$('#state').textContent=(data.status||'idle').toUpperCase();$('#turn').textContent=`turn ${data.turn||0} · level ${data.levels_completed||0}${data.levels_total?'/'+data.levels_total:''}`;let d=data.decision||data.executed_decision;$('#decision').innerHTML=d?.top_actions?pretty(d.top_actions):`<span class=muted>${esc(data.r2_parallel_phase||'Waiting for ranked actions.')}</span>`;$('#explanations').innerHTML=d?.current_explanation?pretty(d.current_explanation):data.current_explanation?pretty(data.current_explanation):'<span class=muted>Waiting for the frame-0 explanation.</span>';let schemas=d?.salient_schemas?.length?d.salient_schemas:data.salient_schemas;$('#schemas').innerHTML=schemas?.length?schemas.map(e=>`<div class=entry>${pretty(e)}</div>`).join(''):`<span class=muted>${esc(data.r2_parallel_phase||'No situated schema is salient yet.')}</span>`;let s=data.scratchpad,q=data.qwen||{};$('#scratch').innerHTML=s?pretty(s):(q.phase==='response-rejected'?`<span class=muted>No scratchpad was accepted. The agent remains at frame 0.<br><br>${esc(q.reason||'Invalid response')}</span>`:'<span class=muted>Waiting for Qwen.</span>');let p=q.awaiting?(q.progress_fraction||0):(q.phase==='written-to-workspace'?1:0);$('#qring').style.setProperty('--p',p);$('#qphase').textContent=String(q.phase||'ready').replaceAll('-',' ').toUpperCase();let basis=String(q.eta_basis||'').includes('prior')?'prior':'learned';$('#qeta').textContent=q.awaiting?`call ${q.call_index} · ${q.elapsed_seconds||0}s elapsed · ${basis} ETA ${q.remaining_seconds||0}s`:(q.phase==='response-rejected'?`agent did not act · ${q.reason||'invalid response'}`:q.phase==='written-to-workspace'?`written in ${q.elapsed_seconds||0}s · next ETA ${q.eta_seconds||0}s`:`${basis} ETA ${q.eta_seconds||0}s`);$('#metadata').innerHTML=data.metadata?pretty(data.metadata):'<span class=muted>Live run metadata is committed in its manifest.</span>';$('#pause').textContent=data.paused?'RESUME':'PAUSE'}function show(i){if(!replay)return;index=Math.max(0,Math.min(i,replay.timeline.length-1));data={...replay.timeline[index],status:'playback',metadata:replay.metadata};$('#scrub').max=replay.timeline.length-1;$('#scrub').value=index;render()}async function refresh(){let o=await api('/api/options');$('#game').innerHTML=o.games.map(g=>`<option>${esc(g)}</option>`).join('');$('#runs').innerHTML=o.runs.map(r=>`<option value="${r.run_id}">${r.game||'?'} L${r.level} · ${r.status} · ${r.actions} actions · ${r.r2_version||'R2'}</option>`).join('')||'<option value="">No stored runs</option>'}async function poll(){if(!replay)try{data=await api('/api/agent');render()}catch(e){}setTimeout(poll,180)}$('#start').onclick=async()=>{replay=null;await api('/api/start',{game:$('#game').value,level:+$('#level').value})};$('#load').onclick=async()=>{let id=$('#runs').value;if(id){replay=await api('/api/replay?run='+encodeURIComponent(id));show(0)}};$('#pause').onclick=()=>replay?clearInterval(timer):api('/api/control',{paused:!data.paused});$('#step').onclick=()=>replay?show(index+1):api('/api/control',{step:true});$('#back').onclick=()=>show(index-1);$('#forward').onclick=()=>show(index+1);$('#scrub').oninput=e=>show(+e.target.value);$('#speed').onchange=e=>{if(!replay)api('/api/control',{speed:+e.target.value})};$('#play').onclick=()=>{if(!replay)return;clearInterval(timer);timer=setInterval(()=>{if(index>=replay.timeline.length-1)clearInterval(timer);else show(index+1)},1000/+$('#speed').value)};refresh();poll();</script></body></html>"""


# The center column is not necessarily square. Size the canvas element from
# both available dimensions so overflow can never crop a frame.
PAGE = PAGE.replace(
    "</body>",
    """<script>
function fitArcadeBoard(){
  const c=document.querySelector('#board'), w=c.parentElement;
  const s=Math.max(1,Math.floor(Math.min(w.clientWidth,w.clientHeight)));
  c.style.width=s+'px'; c.style.height=s+'px';
}
new ResizeObserver(fitArcadeBoard).observe(document.querySelector('.canvas-wrap'));
addEventListener('resize',fitArcadeBoard); fitArcadeBoard();
</script></body>""",
)
PAGE = PAGE.replace(
    '<div class=canvas-wrap><canvas id=board width=800 height=800></canvas></div>',
    '<div class=canvas-wrap><div id=boardhud></div><canvas id=board width=800 height=800></canvas></div>',
)
PAGE = PAGE.replace(
    "</head>",
    """<style>
.canvas-wrap{position:relative}
#boardhud{position:absolute;z-index:2;top:10px;left:10px;max-width:calc(100% - 20px);padding:6px 8px;background:#07100bdd;border:1px solid #426050;border-radius:5px;color:var(--lime);font-size:12px;letter-spacing:.05em;pointer-events:none}
</style></head>""",
)
PAGE = PAGE.replace(
    "</body>",
    """<script>
const renderWithBudget = render;
render = function(){
  renderWithBudget();
  const budget = data.action_budget ?? data.metadata?.action_budget;
  const turn = Number(data.turn || 0);
  const remaining = budget == null ? '—' : Math.max(0, Number(budget) - turn);
  const level = data.levels_total ? `${data.levels_completed || 0}/${data.levels_total}` : '—';
  document.querySelector('#boardhud').textContent = `ACTION ${turn}/${budget ?? '—'} · ${remaining} LEFT  |  LEVEL ${level}  |  ${String(data.status || 'idle').toUpperCase()}`;
};
</script></body>""",
)
PAGE = PAGE.replace(
    "$('#scratch').innerHTML=s?pretty(s):",
    "$('#scratch').innerHTML=s?(typeof s==='string'?`<pre>${esc(s)}</pre>`:s.natural_language?`<pre>${esc(s.natural_language)}</pre>${(s.r2_action_traces||[]).length?'<div class=entry><small>R2 OBSERVATION TRACE</small><br>'+s.r2_action_traces.map(esc).join('<br>'):''}`:pretty(s)):",
)
PAGE = PAGE.replace(
    '<button id=start>START AGENT</button>',
    '<button id=start>START AGENT</button><button id=reset>RESET</button>',
)
PAGE = PAGE.replace(
    "$('#start').onclick=async()=>{replay=null;await api('/api/start',{game:$('#game').value,level:+$('#level').value})};",
    "$('#start').onclick=async()=>{replay=null;await api('/api/start',{game:$('#game').value,level:+$('#level').value})};$('#reset').onclick=async()=>{replay=null;clearInterval(timer);data=await api('/api/reset',{});render()};",
)


def serve(runtime: Any, start_agent: Callable[[str, int], None], *, games: Sequence[str], runs_root: Path, host: str = "127.0.0.1", port: int = 8767) -> None:
    lock = threading.Lock(); started = False; store = ReplayStore(runs_root)
    allowed_games = tuple(sorted(set(str(item) for item in games)))

    def run_agent(game: str, level: int) -> None:
        nonlocal started
        try:
            start_agent(game, level)
        finally:
            runtime.finish_reset()
            with lock:
                started = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None: pass
        def send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(value).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def body(self) -> dict[str, Any]:
            value = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
            if not isinstance(value, dict): raise ValueError("body must be an object")
            return value
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            try:
                if parsed.path in {"/", "/arcade"}:
                    body = PAGE.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
                elif parsed.path == "/api/agent": self.send_json(runtime.read())
                elif parsed.path == "/api/options": self.send_json({"games": allowed_games, "runs": store.runs()})
                elif parsed.path == "/api/replay": self.send_json(store.replay(parse_qs(parsed.query).get("run", [""])[0]))
                else: self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except (ValueError, TypeError) as error: self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        def do_POST(self) -> None:
            nonlocal started
            try:
                body = self.body()
                if self.path == "/api/control": self.send_json(runtime.configure(paused=body.get("paused"), speed=body.get("speed"), step=bool(body.get("step", False)))); return
                if self.path == "/api/reset":
                    with lock: active = started
                    runtime.request_reset()
                    if not active: runtime.finish_reset()
                    self.send_json(runtime.read()); return
                if self.path == "/api/start":
                    game, level = str(body.get("game", "")), int(body.get("level", 1))
                    if game not in allowed_games: raise ValueError("unknown game")
                    if not 1 <= level <= 100: raise ValueError("level must be between 1 and 100")
                    with lock:
                        if started: raise ValueError("this server already has a live session; restart it for another fresh run")
                        started = True; threading.Thread(target=run_agent, args=(game, level), name="one-action-agent", daemon=True).start()
                    self.send_json(runtime.read()); return
                self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except (ValueError, TypeError, json.JSONDecodeError) as error: self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    server = ThreadingHTTPServer((host, port), Handler); print(f"Reflector agent arcade: http://{host}:{server.server_port}/arcade", flush=True)
    try: server.serve_forever()
    finally: server.server_close()
