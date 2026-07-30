type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

interface Run {
  path: string; name: string; score: number; levels_completed: number;
  levels_total: number; games_completed: number; games_total: number;
  actions: number; modified: number; source_commit?: string;
}
interface Game {
  game: string; levels_completed: number; levels_total: number; score: number;
  actions: number; completed: boolean; report: string; level_actions: number[];
}
interface Log {
  sequence: number; level: number; state: string; action_id: number;
  reason: string; result: string[]; new: Record<string, number>;
}
interface Snapshot {
  generated_at: string; workspace: string; status: "running" | "idle";
  current: null | {
    active: boolean; game: string; candidate_id: string; agent_version: string;
    inference_fingerprint: string; level: number; state: string; sequence: number;
    objects: number; stream: string; modified: number;
    action: { action_id: number; data: Record<string, number>; reason: string };
    diagnostics: Record<string, Json>;
  };
  offspring: null | Record<string, Json>;
  best_full: Run | null; latest_run: Run | null; runs: Run[];
  games: Game[]; logs: Log[];
  artifacts: { path: string; kind: string; modified: number }[];
}

const app = document.querySelector<HTMLDivElement>("#app")!;
let last: Snapshot | null = null;
let connected = false;
let selectedGame = "";

const esc = (value: unknown) => String(value ?? "—")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const short = (value: unknown, n = 14) => {
  const text = String(value ?? "");
  return text.length > n ? `${text.slice(0, n)}…` : text || "—";
};
const score = (value: number | undefined) => Number(value ?? 0).toFixed(3);
const ago = (timestamp: number) => {
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - timestamp));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
};
const pct = (a: number, b: number) => b ? Math.round(a / b * 100) : 0;

function levelMatrix(games: Game[]): string {
  const max = Math.max(1, ...games.map((game) => game.levels_total));
  return `<div class="matrix-scroll"><div class="matrix" style="--levels:${max}">
    <div class="matrix-corner">GAME</div>
    ${Array.from({ length: max }, (_, i) => `<div class="matrix-head">L${i + 1}</div>`).join("")}
    ${games.map((game) => `
      <button class="matrix-name ${selectedGame === game.game ? "selected" : ""}" data-game="${esc(game.game)}">${esc(game.game)}</button>
      ${Array.from({ length: max }, (_, index) => {
        const exists = index < game.levels_total;
        const done = index < game.levels_completed;
        const actions = game.level_actions[index] ?? 0;
        return `<div class="cell ${!exists ? "void" : done ? "done" : "open"}" title="${esc(game.game)} · level ${index + 1}${done ? ` · ${actions} actions` : " · incomplete"}"><span>${done ? "✓" : ""}</span></div>`;
      }).join("")}
    `).join("")}
  </div></div>`;
}

function diagnostics(values: Record<string, Json>): string {
  const entries = Object.entries(values).slice(0, 14);
  if (!entries.length) return `<p class="empty">No active mechanism diagnostics.</p>`;
  return `<div class="diag-grid">${entries.map(([key, value]) =>
    `<div><span>${esc(key.replaceAll("_", " "))}</span><strong>${esc(Array.isArray(value) ? value.length : value)}</strong></div>`
  ).join("")}</div>`;
}

function render(data: Snapshot): void {
  last = data;
  const best = data.best_full;
  const current = data.current;
  const completed = data.games.reduce((sum, game) => sum + game.levels_completed, 0);
  const total = data.games.reduce((sum, game) => sum + game.levels_total, 0);
  const game = data.games.find((item) => item.game === selectedGame);
  app.innerHTML = `
    <header>
      <a class="brand" href="/monitor.html"><span>R</span><div><strong>REFLECTOR</strong><small>LIVE MISSION CONTROL</small></div></a>
      <div class="connection ${connected ? "on" : ""}"><i></i>${connected ? "STREAMING" : "RECONNECTING"}</div>
      <nav><a href="/monitor.html" class="active">Live</a><a href="/">Replay lab</a></nav>
    </header>
    <main>
      <section class="intro">
        <div><p class="kicker">OFFSPRING OBSERVATORY / LOCAL EVIDENCE</p><h1>Watch the mind<br><em>become a model.</em></h1>
        <p class="lede">Every action, level, hypothesis and verified best—streamed directly from the run artifacts.</p></div>
        <div class="run-state ${data.status}">
          <div class="orbit"><i></i><span>${data.status === "running" ? "RUNNING" : "STANDING BY"}</span></div>
          <small>${current ? `${esc(current.game)} · updated ${ago(current.modified)}` : "Awaiting a cognitive stream"}</small>
        </div>
      </section>

      <section class="score-strip">
        <article class="score-primary">
          <span class="label">CURRENT VERIFIED BEST</span>
          <strong>${score(best?.score)}<small>/100</small></strong>
          <div class="bar"><i style="width:${Math.min(100, best?.score ?? 0)}%"></i><b style="left:20%">20 goal</b></div>
          <p>${best ? `${best.levels_completed}/${best.levels_total} levels · ${best.games_completed}/${best.games_total} games complete` : "No 25-game scorecard found"}</p>
        </article>
        <article><span class="label">LEVEL COVERAGE</span><strong>${completed}<small> / ${total}</small></strong><p>${pct(completed, total)}% across discovered game bests</p></article>
        <article><span class="label">LATEST RUN</span><strong>${score(data.latest_run?.score)}</strong><p>${esc(data.latest_run?.name ?? "No run")}</p></article>
        <article><span class="label">OFFSPRING</span><strong class="mono">${short(data.offspring?.candidate_id, 18)}</strong><p>generation ${esc(data.offspring?.generation)}</p></article>
      </section>

      <section class="live-grid">
        <article class="panel current-panel">
          <div class="panel-title"><div><span class="eyebrow">NOW / COGNITIVE STREAM</span><h2>${current ? esc(current.game) : "No active game"}</h2></div><span class="level-badge">LEVEL ${current?.level ?? "—"}</span></div>
          ${current ? `
            <div class="action">
              <span>${esc(current.action?.action_id ?? "—")}</span>
              <div><small>ACTION ${esc(current.sequence)}</small><strong>${esc(current.action?.reason ?? "Waiting for decision")}</strong></div>
              <code>${esc(JSON.stringify(current.action?.data ?? {}))}</code>
            </div>
            <div class="current-meta"><span>STATE <b>${esc(current.state)}</b></span><span>OBJECTS <b>${esc(current.objects)}</b></span><span>POLICY <b>${esc(current.agent_version)}</b></span></div>
            <details open><summary>Main mechanism outputs</summary>${diagnostics(current.diagnostics)}</details>
            <p class="source">${esc(current.stream)}</p>
          ` : `<div class="waiting"><span>◌</span><strong>Ready for the next offspring</strong><p>The stream connects automatically when a cognitive JSONL file starts changing.</p></div>`}
        </article>
        <article class="panel offspring-panel">
          <div class="panel-title"><div><span class="eyebrow">LINEAGE / CURRENT OFFSPRING</span><h2>${short(data.offspring?.candidate_id, 24)}</h2></div></div>
          <dl>
            <div><dt>Parent</dt><dd>${short(data.offspring?.parent_id, 22)}</dd></div>
            <div><dt>Generation</dt><dd>${esc(data.offspring?.generation)}</dd></div>
            <div><dt>Mutation</dt><dd>${esc(data.offspring?.mutation_source)}</dd></div>
            <div><dt>Fingerprint</dt><dd>${short(data.offspring?.inference_fingerprint, 22)}</dd></div>
          </dl>
          <blockquote>${esc(data.offspring?.rationale ?? "No candidate metadata discovered.")}</blockquote>
          <div class="lineage"><i></i><span>PARENT</span><b>→</b><i class="child"></i><span>OFFSPRING</span></div>
        </article>
      </section>

      <section class="panel matrix-panel">
        <div class="panel-title"><div><span class="eyebrow">BEST EVIDENCE / ALL GAMES</span><h2>Games × levels</h2></div>
          <div class="legend"><span><i class="done"></i>Complete</span><span><i class="open"></i>Open</span><span><i class="void"></i>N/A</span></div></div>
        ${levelMatrix(data.games)}
        ${game ? `<div class="game-focus"><strong>${esc(game.game)}</strong><span>${game.levels_completed}/${game.levels_total} levels</span><span>${score(game.score)} score</span><span>${game.actions} actions</span><span>best in ${esc(game.report)}</span></div>` : ""}
      </section>

      <section class="lower-grid">
        <article class="panel terminal">
          <div class="panel-title"><div><span class="eyebrow">STREAM / LAST ${data.logs.length} EVENTS</span><h2>Decision log</h2></div><span class="live-dot">LIVE</span></div>
          <div class="log-head"><span>SEQ</span><span>LVL</span><span>ACTION</span><span>RATIONALE / OBSERVED OUTPUT</span></div>
          <div class="logs">${data.logs.slice().reverse().map((log) => `
            <div class="log-row"><span>${esc(log.sequence)}</span><span>${esc(log.level)}</span><b>A${esc(log.action_id)}</b>
            <div><strong>${esc(log.reason)}</strong>${log.result.length ? `<small>${esc(log.result.slice(0, 3).join(" · "))}</small>` : ""}</div></div>
          `).join("") || `<p class="empty">No cognitive events yet.</p>`}</div>
        </article>
        <article class="panel runs">
          <div class="panel-title"><div><span class="eyebrow">OUTPUTS / SCORECARDS</span><h2>Recent runs</h2></div></div>
          <div class="run-list">${data.runs.slice(0, 7).map((run) => `
            <div><i class="${run.games_total >= 25 ? "official" : ""}"></i><span><strong>${esc(run.name)}</strong><small>${run.games_total} games · ${ago(run.modified)}</small></span><b>${score(run.score)}</b></div>
          `).join("")}</div>
          <div class="artifact-title">LATEST ARTIFACTS</div>
          <div class="artifacts">${data.artifacts.slice(0, 7).map((item) => `<span><b>${esc(item.kind)}</b>${esc(item.path)}</span>`).join("")}</div>
        </article>
      </section>
    </main>
    <footer><span>Read-only local monitor · ${esc(data.workspace)}</span><span>Updated ${new Date(data.generated_at).toLocaleTimeString()}</span></footer>
  `;
  document.querySelectorAll<HTMLElement>("[data-game]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedGame = button.dataset.game ?? "";
      if (last) render(last);
    });
  });
}

async function fetchOnce(): Promise<void> {
  const response = await fetch("/api/live");
  if (!response.ok) throw new Error(`Live API ${response.status}`);
  render(await response.json() as Snapshot);
}

function connectStream(): void {
  const events = new EventSource("/api/live/events");
  events.addEventListener("open", () => { connected = true; if (last) render(last); });
  events.addEventListener("snapshot", (event) => render(JSON.parse((event as MessageEvent).data) as Snapshot));
  events.addEventListener("error", () => { connected = false; if (last) render(last); });
}

fetchOnce()
  .then(() => {
    if (!new URLSearchParams(window.location.search).has("snapshot")) {
      connectStream();
    }
  })
  .catch((error: Error) => {
    app.innerHTML = `<div class="fatal"><strong>Monitor unavailable</strong><p>${esc(error.message)}</p></div>`;
  });
