"""Loopback-only human controller for local public ARC-AGI-3 environments."""

from __future__ import annotations

import json
import argparse
import threading
import time
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ACTION_NAMES = {
    0: "RESET", 1: "ACTION 1", 2: "ACTION 2", 3: "ACTION 3",
    4: "ACTION 4", 5: "ACTION 5", 6: "CLICK", 7: "ACTION 7",
}


class HumanArcade:
    def __init__(self, environments_dir: Path, notes_path: Path) -> None:
        self.environments_dir = environments_dir.resolve()
        self.notes_path = notes_path
        self.arcade: Any = None
        self.environment: Any = None
        self.game: str | None = None
        self.selected_level = 0
        self.completed_levels: set[int] = set()
        self.turn = 0
        self.history: list[dict[str, object]] = []
        self.history_cursor = 0
        self.level_starts: dict[int, int] = {0: 0}
        self.lock = threading.RLock()
        self.agent_scorecards, self.default_agent, self.best_by_game = self._agent_scorecards()

    def games(self) -> list[str]:
        return sorted(path.name for path in self.environments_dir.iterdir() if path.is_dir())

    def _agent_scorecards(self) -> tuple[dict[str, dict[str, object]], str | None, dict[str, dict[str, object]]]:
        """Read complete local Reflector scorecards, keyed by run/version."""
        project_root = Path(__file__).resolve().parents[1]
        configured_reports = os.environ.get("REFLECTOR_REPORTS_DIR")
        report_dirs = (
            [Path(configured_reports)]
            if configured_reports
            else [
                project_root / "reports",
                *sorted(
                    sibling / "reports"
                    for sibling in project_root.parent.glob("reflector*/")
                    if (sibling / "reports").is_dir()
                ),
            ]
        )
        agents: dict[str, dict[str, object]] = {}
        best: dict[str, dict[str, object]] = {}
        reports_dirs = [path for path in report_dirs if path.is_dir()]
        if not reports_dirs:
            return agents, None, best
        for reports_dir in reports_dirs:
          for path in reports_dir.rglob("*.json"):
            try:
                if path.stat().st_size > 30_000_000:
                    continue
                report = json.loads(path.read_text(encoding="utf-8"))
                scorecard = report["scorecard"]
                environments = scorecard["environments"]
            except (OSError, KeyError, TypeError, json.JSONDecodeError):
                continue
            if not isinstance(environments, list):
                continue
            version = path.parent.name if path.name == "official-report.json" else path.stem
            try:
                total_games = int(scorecard.get("total_environments", len(environments)))
                agent = {
                    "version": version,
                    "score": float(scorecard.get("score", 0)),
                    "levels_completed": int(scorecard.get("total_levels_completed", 0)),
                    "levels_total": int(scorecard.get("total_levels", 0)),
                    "actions": int(scorecard.get("total_actions", 0)),
                    "games": {},
                }
            except (TypeError, ValueError):
                continue
            for environment in environments:
                if not isinstance(environment, dict):
                    continue
                game = str(environment.get("id", "")).split("-", 1)[0]
                if not game:
                    continue
                try:
                    item = {
                        "version": version,
                        "score": float(environment.get("score", 0)),
                        "levels_completed": int(environment.get("levels_completed", 0)),
                        "levels_total": int(environment.get("level_count", 0)),
                        "actions": int(environment.get("actions", 0)),
                    }
                except (TypeError, ValueError):
                    continue
                agent["games"][game] = item
                incumbent = best.get(game)
                rank = (item["levels_completed"], item["score"], -item["actions"])
                incumbent_rank = (
                    (incumbent["levels_completed"], incumbent["score"], -incumbent["actions"])
                    if incumbent is not None else None
                )
                if incumbent_rank is None or rank > incumbent_rank:
                    best[game] = item
            # An agent selector is useful only when it supplies a comparable
            # result for every public game; partial probes remain in best_by_game.
            if total_games >= 25 and len(agent["games"]) >= 25:
                agents[version] = agent
        default = max(
            agents,
            key=lambda version: (
                float(agents[version]["score"]),
                int(agents[version]["levels_completed"]),
                -int(agents[version]["actions"]),
            ),
            default=None,
        )
        return agents, default, best

    def _open(self, game: str) -> None:
        """Open a new environment instance without changing the replay journal."""
        from arc_agi import Arcade, OperationMode

        self.close()
        self.arcade = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=str(self.environments_dir),
            recordings_dir=str(self.environments_dir.parent / "human_arcade_recordings"),
        )
        self.environment = self.arcade.make(game, include_frame_data=True)
        if self.environment is None:
            raise RuntimeError("could not open game")
        self.game = game

    def start(self, game: str) -> dict[str, object]:
        if game not in self.games():
            raise ValueError("unknown public game")
        with self.lock:
            self._open(game)
            self.turn = 0
            self.history = []
            self.history_cursor = 0
            self.level_starts = {0: 0}
            self.selected_level = 0
            self.completed_levels = set()
            return self.snapshot()

    def close(self) -> None:
        if self.arcade is not None:
            try:
                self.arcade.close_scorecard()
            except Exception:
                pass
        self.arcade = self.environment = self.game = None

    def snapshot(self) -> dict[str, object]:
        if self.environment is None or self.game is None:
            return {"active": False, "games": self.games()}
        raw = self.environment.observation_space
        frame_value = raw.frame.tolist() if hasattr(raw.frame, "tolist") else raw.frame
        if isinstance(frame_value, list) and frame_value and hasattr(frame_value[-1], "tolist"):
            frame_value = frame_value[-1].tolist()
        while (
            isinstance(frame_value, list)
            and frame_value
            and isinstance(frame_value[0], list)
            and frame_value[0]
            and isinstance(frame_value[0][0], list)
        ):
            frame_value = frame_value[-1]
        frame = [[int(cell) for cell in row] for row in frame_value]
        return {
            "active": True,
            "game": self.game,
            "turn": self.turn,
            "frame": frame,
            "state": raw.state.value,
            "levels_completed": int(raw.levels_completed),
            "levels_total": int(raw.win_levels),
            "current_level": self.selected_level + 1,
            "reachable_levels": list(range(1, int(raw.win_levels) + 1)),
            "completed_levels": sorted(level + 1 for level in self.completed_levels),
            "available_actions": [int(action) for action in raw.available_actions],
            "action_names": {str(key): value for key, value in ACTION_NAMES.items()},
            "notes": self.notes(),
        }

    def act(self, action_id: int, data: dict[str, int]) -> dict[str, object]:
        if self.environment is None or self.game is None:
            raise ValueError("select a game first")
        raw = self.environment.observation_space
        if action_id not in raw.available_actions:
            raise ValueError("action is not currently legal")
        if action_id == 6:
            if set(data) != {"x", "y"} or any(type(value) is not int for value in data.values()):
                raise ValueError("CLICK requires integer x and y")
            if not 0 <= data["x"] < 64 or not 0 <= data["y"] < 64:
                raise ValueError("click coordinates must be within 0..63")
        elif data:
            raise ValueError("only CLICK accepts action data")
        from arcengine import GameAction

        if self.history_cursor < len(self.history):
            self.history = self.history[:self.history_cursor]
            self._rebuild_level_starts()
        action = GameAction.from_id(action_id)
        if data:
            action.set_data(data)
        before_level = int(raw.levels_completed)
        self.environment.step(action, data={**data, "game_id": self.game}, reasoning={"human_arcade": True})
        self.turn += 1
        after_level = int(self.environment.observation_space.levels_completed)
        if after_level > before_level:
            self.completed_levels.add(self.selected_level)
            self.selected_level += after_level - before_level
        self.history.append({"action_id": action_id, "data": dict(data), "level_before": before_level, "level_after": after_level})
        self.history_cursor += 1
        if after_level > before_level:
            self.level_starts.setdefault(after_level, len(self.history))
        return self.snapshot()

    def _rebuild_level_starts(self) -> None:
        self.level_starts = {0: 0}
        for index, entry in enumerate(self.history, start=1):
            if int(entry["level_after"]) > int(entry["level_before"]):
                self.level_starts.setdefault(int(entry["level_after"]), index)

    def go_to_level(self, level: int) -> dict[str, object]:
        """Open any level directly, including levels not previously reached."""
        if self.game is None:
            raise ValueError("select a game first")
        total_levels = int(self.environment.observation_space.win_levels)
        if not 0 <= level < total_levels:
            raise ValueError(f"level must be between 1 and {total_levels}")
        with self.lock:
            game = self.game
            self._open(game)
            self.environment.reset()
            self.environment._game.set_level(level)
            # A reset at action-count zero is a full reset to level 1. Make
            # the next reset a level reset so the selected level is retained.
            self.environment._game._action_count = 1
            self.environment.reset()
            self.turn = 0
            self.history = []
            self.history_cursor = 0
            self.level_starts = {level: 0}
            self.selected_level = level
            return self.snapshot()

    def notes(self) -> list[dict[str, object]]:
        try:
            value = json.loads(self.notes_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(value, list):
            return []
        notes = [item for item in value if isinstance(item, dict) and item.get("game") == self.game]
        for item in notes:
            item.setdefault("level", 1)
        return sorted(notes, key=lambda item: (int(item.get("level", 1)), str(item.get("created_at", ""))))

    def note(self, text: str) -> dict[str, object]:
        cleaned = text.strip()
        if self.game is None or not cleaned:
            raise ValueError("select a game and enter a note")
        if len(cleaned) > 4000:
            raise ValueError("note exceeds 4000 characters")
        try:
            all_notes = json.loads(self.notes_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            all_notes = []
        if not isinstance(all_notes, list):
            all_notes = []
        note = {"id": f"note-{time.time_ns():x}", "game": self.game, "level": int(self.environment.observation_space.levels_completed) + 1, "turn": self.turn, "text": cleaned, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        all_notes.append(note)
        self.notes_path.write_text(json.dumps(all_notes, indent=2) + "\n", encoding="utf-8")
        return note


PAGE = """<!doctype html><meta charset=utf-8><title>Reflector Human Arcade</title>
<style>body{margin:0;background:#090b0f;color:#e8ebef;font:14px ui-monospace,monospace}main{max-width:1200px;margin:auto;padding:22px}select,button,textarea{background:#141920;color:inherit;border:1px solid #38414d;padding:9px;font:inherit}button{cursor:pointer}button:hover{border-color:#d7ff3f;color:#d7ff3f}#board{width:min(760px,100%);aspect-ratio:1;background:#050609;image-rendering:pixelated;border:1px solid #38414d}.grid{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:18px}.actions{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}textarea{width:100%;box-sizing:border-box;min-height:90px}.note{border-left:2px solid #50d8d2;background:#12161c;padding:9px;margin-top:8px;white-space:pre-wrap}small{color:#9ba4b1}.benchmark{color:#d7ff3f;background:#12161c;border-left:2px solid #d7ff3f;padding:9px;max-width:760px}</style>
<main><h1>REFLECTOR / HUMAN ARCADE</h1><p>Choose a public game. You control every action; no policy acts for you.</p><label>BENCHMARK AGENT <select id=agents></select></label><br><br><label>GAME <select id=games></select></label> <button id=start>START FRESH</button><p id=benchmark class=benchmark>Loading local Reflector scorecard…</p><p id=status>Select a game to begin.</p><div id=navigation class=actions></div><div class=grid><section><canvas id=board width=640 height=640></canvas><div id=actions class=actions></div></section><aside><h2>NOTES / GAME + LEVEL INDEX</h2><textarea id=note placeholder="What changed? What do you think this control does?"></textarea><p><button id=save>SAVE NOTE FOR THIS LEVEL</button></p><div id=notes></div></aside></div></main>
<script>let s=null,clickMode=false,agents={};const $=x=>document.querySelector(x);async function api(u,o){let r=await fetch(u,o);let j=await r.json();if(!r.ok)throw Error(j.error);return j}function selectedAgent(){return agents[$('#agents').value]}function fillGames(){let keep=$('#games').value,agent=selectedAgent();$('#games').innerHTML=Object.keys(agent.games).sort().map(g=>{let b=agent.games[g],label=`${g} — ${b.levels_completed}/${b.levels_total} levels, ${b.score.toFixed(2)}`;return `<option value="${g}">${label}</option>`}).join('');if([...$('#games').options].some(o=>o.value===keep))$('#games').value=keep;benchmark()}function benchmark(){let g=$('#games').value,a=selectedAgent(),b=a.games[g];$('#benchmark').textContent=`SELECTED REFLECTOR · ${a.version} · overall ${a.score.toFixed(2)} score, ${a.levels_completed}/${a.levels_total} levels · ${g}: ${b.score.toFixed(2)} score, ${b.levels_completed}/${b.levels_total} levels`}function esc(v){return String(v).replaceAll('&','&amp;').replaceAll('<','&lt;')}function draw(){let c=$('#board'),x=c.getContext('2d'),f=s?.frame||[];x.fillStyle='#050609';x.fillRect(0,0,640,640);if(!f.length)return;let z=Math.min(640/f.length,640/f[0].length),p=['#0a0b0d','#1672f3','#f04444','#26b566','#f5d342','#8c8e95','#d94bc9','#ff8d2a','#67d9e8','#8b4fd8','#e7e9ee','#55a7ff','#ff7580','#7de09d','#fff17a','#fff17a','#c5c8ce'];f.forEach((r,y)=>r.forEach((v,x1)=>{x.fillStyle=p[v]||'#fff';x.fillRect(x1*z,y*z,Math.ceil(z),Math.ceil(z))}))}async function level(n){s=await api('/api/level',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({level:n})});render()}function render(){if(!s)return;$('#status').textContent=`${s.game} · level ${s.current_level}/${s.levels_total} · turn ${s.turn} · ${s.state}`;let prev=s.current_level-1,next=s.current_level+1;$('#navigation').innerHTML=`<button ${s.reachable_levels.includes(prev)?'':'disabled'} id=previous>← PREVIOUS REACHED LEVEL</button><button ${s.reachable_levels.includes(next)?'':'disabled'} id=next>NEXT REACHED LEVEL →</button><small>Navigation reconstructs this session from your own action history. Reached: ${s.reachable_levels.join(', ')}</small>`;$('#previous').onclick=()=>level(prev);$('#next').onclick=()=>level(next);$('#actions').innerHTML=s.available_actions.map(a=>`<button data-a="${a}">${s.action_names[a]}</button>`).join('');document.querySelectorAll('[data-a]').forEach(b=>b.onclick=async()=>{let a=+b.dataset.a;if(a===6){clickMode=true;$('#status').textContent+=' · click a cell'}else{clickMode=false;s=await api('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_id:a,data:{}})});render()}});let groups={};s.notes.forEach(n=>(groups[n.level]??=[]).push(n));$('#notes').innerHTML=Object.entries(groups).map(([level,notes])=>`<h3>${s.game} / LEVEL ${level}</h3>${notes.map(n=>`<div class=note><small>turn ${n.turn} · ${n.created_at}</small><br>${esc(n.text)}</div>`).join('')}`).join('')||'<small>No notes for this game yet.</small>';draw()}async function load(){let d=await api('/api/games');agents=d.agents||{};let choices=Object.values(agents).sort((a,b)=>b.score-a.score);$('#agents').innerHTML=choices.map(a=>`<option value="${a.version}">${a.version} — ${a.score.toFixed(2)} overall, ${a.levels_completed}/${a.levels_total} levels</option>`).join('');$('#agents').value=d.default_agent;$('#agents').onchange=fillGames;fillGames();$('#games').onchange=benchmark}$('#start').onclick=async()=>{s=await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game:$('#games').value})});render()};$('#board').onclick=async e=>{if(!clickMode||!s)return;let r=e.target.getBoundingClientRect(),w=s.frame[0].length,h=s.frame.length,x=Math.floor((e.clientX-r.left)*w/r.width),y=Math.floor((e.clientY-r.top)*h/r.height);clickMode=false;s=await api('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_id:6,data:{x,y}})});render()};$('#save').onclick=async()=>{let text=$('#note').value;s=await api('/api/note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});$('#note').value='';render()};load()</script>"""


# Level navigation is intentionally independent of the session's reached-level
# history. The page is still a static string, so keep the UI policy explicit in
# one place rather than duplicating it in the HTML template.
PAGE = (
    PAGE.replace("PREVIOUS REACHED LEVEL", "PREVIOUS LEVEL")
    .replace("NEXT REACHED LEVEL", "NEXT LEVEL")
    .replace("id=previous>", "id=previous-level>")
    .replace("id=next>", "id=next-level>")
    .replace("$('#previous').onclick", "$('#previous-level').onclick")
    .replace("$('#next').onclick", "$('#next-level').onclick")
    .replace(
        "async function level(n){s=await api('/api/level',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({level:n})});render()}",
        "async function level(n){try{s=await api('/api/level',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({level:n})});render()}catch(error){$('#status').textContent=`Navigation failed: ${error.message||error}`}}",
    )
    .replace("s.reachable_levels.includes(prev)?'':'disabled'", "prev < 1?'disabled':' '")
    .replace("s.reachable_levels.includes(next)?'':'disabled'", "next > s.levels_total?'disabled':' '")
    .replace(
        "Navigation reconstructs this session from your own action history. Reached: ${s.reachable_levels.join(', ')}",
        "Any level can be opened directly.",
    )
    .replace(
        "Any level can be opened directly.</small>",
        "Any level can be opened directly. ${s.completed_levels?.includes(s.current_level)?'<span style=\"color:#7de09d\">● beaten</span>':''}</small>",
    )
)


class Handler(BaseHTTPRequestHandler):
    server: "Server"
    def log_message(self, *_: object) -> None: pass
    def _json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _body(self) -> dict[str, object]:
        value = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if not isinstance(value, dict): raise ValueError("body must be an object")
        return value
    def do_GET(self) -> None:
        if self.path == "/":
            body = PAGE.encode(); self.send_response(200); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path == "/api/games": self._json({"games": self.server.arcade.games(), "agents": self.server.arcade.agent_scorecards, "default_agent": self.server.arcade.default_agent, "best_by_game": self.server.arcade.best_by_game}); return
        if self.path == "/api/session": self._json(self.server.arcade.snapshot()); return
        self._json({"error":"not found"}, HTTPStatus.NOT_FOUND)
    def do_POST(self) -> None:
        try:
            body = self._body()
            if self.path == "/api/start": self._json(self.server.arcade.start(str(body.get("game", "")))); return
            if self.path == "/api/action": self._json(self.server.arcade.act(body.get("action_id"), body.get("data", {}))); return
            if self.path == "/api/level": self._json(self.server.arcade.go_to_level(int(body.get("level", 0)) - 1)); return
            if self.path == "/api/note": self.server.arcade.note(str(body.get("text", ""))); self._json(self.server.arcade.snapshot()); return
            self._json({"error":"not found"}, HTTPStatus.NOT_FOUND)
        except (TypeError, ValueError, json.JSONDecodeError) as error: self._json({"error":str(error)}, HTTPStatus.BAD_REQUEST)


class Server(ThreadingHTTPServer):
    arcade: HumanArcade


def serve(
    environments_dir: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    notes_path: Path | None = None,
) -> None:
    """Serve the arcade with its copied notes unless a journal is supplied."""
    journal = notes_path or Path(__file__).with_name("notes.json")
    server = Server((host, port), Handler); server.arcade = HumanArcade(environments_dir, journal)
    print(f"Reflector human arcade: http://{host}:{server.server_port}")
    try: server.serve_forever()
    finally: server.arcade.close(); server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Reflector human arcade")
    parser.add_argument(
        "--environments-dir",
        type=Path,
        default=Path("/home/pauloabelha/arc-agi-3-public-games-2026/environment_files"),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--notes-path",
        type=Path,
        default=Path(__file__).with_name("notes.json"),
        help="JSON note journal; defaults to the journal copied into reflector2/arcade",
    )
    args = parser.parse_args()
    serve(args.environments_dir, host=args.host, port=args.port, notes_path=args.notes_path)
