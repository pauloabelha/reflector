import type {
  BranchReport,
  CandidateRecord,
  Concept,
  ConceptType,
  ExperimentReport,
  Graph,
  Hypothesis,
  Manifest,
  Replay,
  ReplayStep,
  Schema,
  SchemaFamily,
} from "./types.js";

const COLORS = [
  "#0a0b0d", "#1672f3", "#f04444", "#26b566",
  "#f5d342", "#8c8e95", "#d94bc9", "#ff8d2a",
  "#67d9e8", "#8b4fd8", "#e7e9ee", "#55a7ff",
  "#ff7580", "#7de09d", "#fff17a", "#c5c8ce",
];

const app = document.querySelector<HTMLDivElement>("#app")!;

let replay: Replay;
let current = 0;
let playing = false;
let timer: number | undefined;
let speed = 1;
let activeModelTab = "concepts";
let manifests: Manifest[] = [];
let experiment: ExperimentReport | null = null;
let branch: BranchReport | null = null;
let selectedCandidate: string | null = null;

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const payload = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `Request failed: ${response.status}`);
  return payload;
}

function escapeHtml(value: unknown): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function short(value: string, size = 13): string {
  return value.length > size ? `${value.slice(0, size)}…` : value;
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function actionName(action: number): string {
  return ({
    0: "RESET", 1: "UP", 2: "DOWN", 3: "LEFT",
    4: "RIGHT", 5: "ACT", 6: "CLICK", 7: "ALT",
  } as Record<number, string>)[action] ?? `ACTION ${action}`;
}

function stateTone(state: string): string {
  if (state === "WIN") return "positive";
  if (state.includes("OVER")) return "negative";
  return "active";
}

function shell(): string {
  const step = replay.steps[current];
  if (!step) return `<main class="error">Trace has no replayable steps.</main>`;
  return `
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark">R</span>
        <div><strong>REFLECTOR</strong><small>SYMBOLIC INSTRUMENT / ${escapeHtml(replay.trace.agent_version)}</small></div>
      </div>
      <div class="run-meta">
        <span class="signal"></span>
        <span>LOCAL REPLAY</span>
        <span class="divider"></span>
        <span>${replay.trace.step_count} OBSERVATIONS</span>
        <span class="divider"></span>
        <span>DSL v${replay.trace.format_version}</span>
      </div>
      <div class="status-pill ${stateTone(step.observation.state)}">${escapeHtml(step.observation.state)}</div>
    </header>
    <main>
      <section class="hero-grid">
        <article class="panel board-panel">
          <div class="panel-head">
            <div><span class="eyebrow">EPISODE REPLAY</span><h1>Perception field</h1></div>
            <div class="level-readout"><small>LEVELS</small><strong>${step.observation.levels_completed}</strong></div>
          </div>
          <div class="board-wrap">
            <canvas id="board" aria-label="ARC board at step ${current}"></canvas>
            <div class="board-coordinates"><span>0,0</span><span>${step.observation.frame[0]?.length ?? 0} × ${step.observation.frame.length}</span></div>
          </div>
          ${controls()}
          ${timeline()}
        </article>
        <aside class="panel decision-panel">
          ${decisionInspector(step)}
        </aside>
      </section>
      <section class="analysis-grid">
        <article class="panel model-panel">
          ${modelInspector(step)}
        </article>
        <article class="panel objects-panel">
          ${objectInspector(step)}
        </article>
      </section>
      <section class="panel population-panel">
        ${populationView()}
      </section>
    </main>
    <footer>
      <span>Offline development surface · never packaged for Kaggle inference</span>
      <span>Recorded outcomes are evidence; trace branches are not environment rollouts.</span>
    </footer>
  `;
}

function controls(): string {
  return `
    <div class="transport">
      <button data-control="first" aria-label="First step">↤</button>
      <button data-control="prev" aria-label="Previous step">←</button>
      <button class="play" data-control="play" aria-label="${playing ? "Pause" : "Play"}">${playing ? "Ⅱ" : "▶"}</button>
      <button data-control="next" aria-label="Next step">→</button>
      <button data-control="last" aria-label="Last step">↦</button>
      <div class="step-counter"><span>STEP</span><strong>${String(current + 1).padStart(2, "0")}</strong><span>/ ${String(replay.steps.length).padStart(2, "0")}</span></div>
      <label class="speed">SPEED
        <select id="speed">
          ${[0.5, 1, 2, 4].map((value) => `<option value="${value}" ${speed === value ? "selected" : ""}>${value}×</option>`).join("")}
        </select>
      </label>
    </div>
  `;
}

function timeline(): string {
  return `
    <div class="timeline" aria-label="Episode timeline">
      <div class="timeline-rail"></div>
      ${replay.steps.map((step, index) => {
        const events = step.incoming_transition?.result ?? [];
        const className = [
          "timeline-node",
          index === current ? "selected" : "",
          step.new_concepts.length ? "concept-born" : "",
          step.new_abstractions.length ? "abstraction-born" : "",
          events.some((event) => event.startsWith("level_advanced")) ? "advanced" : "",
        ].join(" ");
        return `<button class="${className}" style="left:${replay.steps.length === 1 ? 50 : index / (replay.steps.length - 1) * 100}%" data-step="${index}" title="Step ${index + 1}: ${actionName(step.recorded_decision.action_id)}"><span>${index + 1}</span></button>`;
      }).join("")}
    </div>
  `;
}

function decisionInspector(step: ReplayStep): string {
  const actualEvents = step.incoming_transition?.result ?? [];
  return `
    <div class="panel-head compact">
      <div><span class="eyebrow">DECISION / ${String(step.index + 1).padStart(2, "0")}</span><h2>Action rationale</h2></div>
      <span class="match ${step.decision_matches ? "yes" : "no"}">${step.decision_matches ? "DETERMINISTIC" : "DIVERGED"}</span>
    </div>
    <div class="action-card">
      <span class="action-id">${step.replayed_decision.action_id}</span>
      <div><small>SELECTED ACTION</small><strong>${actionName(step.replayed_decision.action_id)}</strong></div>
      ${Object.keys(step.replayed_decision.data).length ? `<code>${escapeHtml(JSON.stringify(step.replayed_decision.data))}</code>` : ""}
    </div>
    <p class="reason">${escapeHtml(step.replayed_decision.reason)}</p>
    <div class="mini-grid">
      <div><small>PLANNER WORK</small><strong>${step.planner_expansions}</strong><span>expansions</span></div>
      <div><small>PLAN</small><strong>${step.plan_actions.length ? step.plan_actions.join(" → ") : "—"}</strong><span>actions</span></div>
    </div>
    <div class="comparison">
      <div class="comparison-head"><h3>Prediction / evidence</h3><span>p(event | action)</span></div>
      <div class="event-list">
        ${step.predictions.length ? step.predictions.map((prediction) => `
          <div class="event-row predicted"><span>${escapeHtml(prediction.event)}</span><strong>${percent(prediction.probability)}</strong></div>
        `).join("") : `<div class="empty">No learned effect prediction yet.</div>`}
        ${actualEvents.map((event) => `<div class="event-row actual"><span>${escapeHtml(event)}</span><strong>OBSERVED</strong></div>`).join("")}
      </div>
    </div>
    <div class="experiment-callout">
      <small>ACTIVE QUESTION</small>
      <p>${escapeHtml(step.experiment ?? "No explicit experiment at this step.")}</p>
    </div>
    ${branchControls()}
  `;
}

function branchControls(): string {
  return `
    <details class="branch" ${branch ? "open" : ""}>
      <summary>Branch policy from this step <span>trace-only</span></summary>
      <div class="branch-form">
        <label>Information weight<input id="branch-information" type="number" min="0" max="100" step="0.25" value="${replay.config.information_weight}"></label>
        <label>Planner budget<input id="branch-budget" type="number" min="1" max="512" step="1" value="${replay.config.planner_max_expansions}"></label>
        <button id="run-branch">Run branch</button>
      </div>
      ${branch ? `<div class="branch-result"><strong>${branch.divergences} divergent decisions</strong><p>${escapeHtml(branch.limitation)}</p><div>${branch.steps.map((item) => `<span class="${item.decision_matches ? "" : "diverged"}">${item.index + 1}:${item.replayed_decision.action_id}</span>`).join("")}</div></div>` : ""}
    </details>
  `;
}

function modelInspector(step: ReplayStep): string {
  const state = step.symbolic_state;
  const counts = {
    concepts: state.concepts.concepts.length,
    schemas: state.schemas.schemas.length,
    families: state.abstractions.schema_families.length + state.abstractions.concept_types.length,
    hypotheses: state.hypotheses.causal.length + state.hypotheses.temporal.length,
    graph: state.dependency_graph.nodes.length,
    language: state.abstractions.language_operators.length,
  };
  return `
    <div class="panel-head">
      <div><span class="eyebrow">WORLD MODEL</span><h2>Symbolic state</h2></div>
      <span class="digest">FRAME ${short(step.scene.frame_digest, 9)}</span>
    </div>
    <nav class="tabs">
      ${Object.entries(counts).map(([name, count]) => `<button class="${activeModelTab === name ? "active" : ""}" data-tab="${name}">${name}<span>${count}</span></button>`).join("")}
    </nav>
    <div class="tab-content">${modelTab(state, activeModelTab)}</div>
  `;
}

function modelTab(state: ReplayStep["symbolic_state"], tab: string): string {
  if (tab === "concepts") return conceptList(state.concepts.concepts, state.dependency_graph);
  if (tab === "schemas") return schemaList(state.schemas.schemas);
  if (tab === "families") return familyList(state.abstractions.schema_families, state.abstractions.concept_types);
  if (tab === "hypotheses") return hypothesisList([...state.hypotheses.causal, ...state.hypotheses.temporal]);
  if (tab === "graph") return graphView(state.dependency_graph);
  return languageView(state.schemas.schemas, state.abstractions);
}

function conceptList(concepts: Concept[], graph: Graph): string {
  if (!concepts.length) return emptyState("No retained concepts yet", "A proposal appears only after repeated evidence pays its complexity cost.");
  return `<div class="card-list">${concepts.map((concept) => {
    const children = graph.edges.filter((edge) => edge.source === concept.concept_id);
    return `<article class="symbol-card concept-card">
      <div class="symbol-title"><span class="type-icon">C</span><div><strong>${escapeHtml(concept.name)}</strong><small>${escapeHtml(concept.kind)} · ${short(concept.concept_id)}</small></div><span class="utility">+${concept.utility.toFixed(1)} U</span></div>
      <p>${concept.definition.map(escapeHtml).join(" ∧ ")}</p>
      <div class="evidence-bar"><span style="width:${Math.min(100, concept.support * 18)}%"></span></div>
      <footer><span>${concept.support} evidence</span><span>${concept.complexity} bits cost</span><span>${concept.counterfactual_savings.toFixed(0)} recoverable</span></footer>
      <details><summary>Evidence & dependencies</summary><code>${concept.evidence.map(escapeHtml).join("\n") || "none"}</code><p>${children.length} graph dependencies · active · no retirement evidence</p></details>
    </article>`;
  }).join("")}</div>`;
}

function schemaList(schemas: Schema[]): string {
  if (!schemas.length) return emptyState("No induced schemas", "The first transition will produce context + action → result evidence.");
  return `<div class="schema-table">
    <div class="table-head"><span>SCHEMA</span><span>RULE</span><span>SUPPORT</span><span>RELIABILITY</span></div>
    ${schemas.map((schema) => `<div class="schema-row">
      <code>${short(schema.schema_id)}</code>
      <div><span class="context">${schema.context.map(escapeHtml).join(" + ")}</span><strong> + ${actionName(schema.action_id)} → ${schema.result.map(escapeHtml).join(", ")}</strong></div>
      <span>${schema.support}/${schema.opportunities}</span>
      <span class="confidence"><i style="width:${schema.reliability * 100}%"></i><b>${percent(schema.reliability)}</b></span>
    </div>`).join("")}
  </div>`;
}

function familyList(families: SchemaFamily[], conceptTypes: ConceptType[]): string {
  if (!families.length && !conceptTypes.length) return emptyState("No higher-order abstractions", "Schema families and typed parents must reduce description length after their complexity charge.");
  return `<div class="card-list">
    ${families.map((family) => `<article class="symbol-card family-card">
      <div class="symbol-title"><span class="type-icon family">F</span><div><strong>${actionName(family.action_id)} → ${family.result_predicates.map(escapeHtml).join(", ")}</strong><small>${short(family.family_id, 24)}</small></div><span class="utility">+${family.utility.toFixed(1)} U</span></div>
      <p>${family.shared_context.map(escapeHtml).join(" ∧ ") || "context-invariant family"}</p>
      <footer><span>${family.member_schemas.length} schemas</span><span>${family.support} support</span><span>${family.raw_description_length} → ${family.compiled_description_length} units</span></footer>
      <details><summary>Member evidence</summary><code>${family.member_schemas.map(escapeHtml).join("\n")}</code></details>
    </article>`).join("")}
    ${conceptTypes.map((conceptType) => `<article class="symbol-card type-card">
      <div class="symbol-title"><span class="type-icon concept-type">T</span><div><strong>${escapeHtml(conceptType.name)}</strong><small>${short(conceptType.type_id, 24)}</small></div><span class="utility">+${conceptType.utility.toFixed(1)} U</span></div>
      <p>Typed parent of ${conceptType.children.length} evidence-backed concepts.</p>
      <footer><span>${conceptType.support} support</span><span>${conceptType.complexity} cost</span><span>${conceptType.raw_description_length} → ${conceptType.compiled_description_length}</span></footer>
      <details><summary>Children & evidence</summary><code>${conceptType.children.map(escapeHtml).join("\n")}</code></details>
    </article>`).join("")}
  </div>`;
}

function hypothesisList(items: Hypothesis[]): string {
  if (!items.length) return emptyState("No hypotheses yet", "Controlled action/effect and temporal comparisons accumulate online.");
  return `<div class="card-list compact-list">${items.map((item) => `<article class="symbol-card">
    <div class="symbol-title"><span class="type-icon hypothesis">H</span><div><strong>${escapeHtml(item.effect ?? `${item.antecedent} → ${item.consequent}`)}</strong><small>${short(item.hypothesis_id, 24)}</small></div><span class="utility">${percent(item.confidence)}</span></div>
    <footer><span>${item.action_id === undefined ? "temporal" : `action ${item.action_id}`}</span><span>support ${item.support}</span><span>${item.strength === undefined ? "Beta-smoothed" : `strength ${item.strength.toFixed(2)}`}</span></footer>
  </article>`).join("")}</div>`;
}

function graphView(graph: Graph): string {
  if (!graph.nodes.length) return emptyState("Graph is empty", "Nodes appear with schemas, hypotheses, and concepts.");
  const width = 760;
  const height = 330;
  const positions = new Map(graph.nodes.map((node, index) => {
    const lanes = { concept: 0, concept_type: 0, language_operator: 0, causal_hypothesis: 1, temporal_hypothesis: 1, language_version: 1, schema_family: 1, schema: 2 } as Record<string, number>;
    const lane = lanes[node.kind] ?? 1;
    const inLane = graph.nodes.filter((other) => (lanes[other.kind] ?? 1) === lane);
    const laneIndex = inLane.findIndex((other) => other.id === node.id);
    return [node.id, { x: 100 + lane * 280, y: 45 + laneIndex * (260 / Math.max(1, inLane.length - 1)) }] as const;
  }));
  return `<div class="graph-wrap"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Concept and schema dependency graph">
    ${graph.edges.map((edge) => {
      const a = positions.get(edge.source); const b = positions.get(edge.target);
      return a && b ? `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"><title>${edge.relation}</title></line>` : "";
    }).join("")}
    ${graph.nodes.map((node) => {
      const point = positions.get(node.id)!;
      return `<g class="node ${node.kind}" transform="translate(${point.x} ${point.y})"><circle r="9"></circle><text x="15" y="4">${escapeHtml(short(node.id, 16))}</text><title>${escapeHtml(node.kind)}: ${escapeHtml(node.id)}</title></g>`;
    }).join("")}
  </svg><div class="graph-legend"><span class="concept">concept</span><span class="hypothesis">hypothesis</span><span class="schema">schema</span></div></div>`;
}

function predicateInventory(schemas: Schema[]): string[] {
  const terms = schemas.flatMap((schema) => [...schema.context, ...schema.result]);
  return [...new Set(terms.map((term) => term.split("(", 1)[0] ?? term))].sort();
}

function languageView(schemas: Schema[], abstractions: ReplayStep["symbolic_state"]["abstractions"]): string {
  const predicates = predicateInventory(schemas);
  const currentVersion = abstractions.language_history.at(-1);
  return `<div class="language-view">
    <div class="language-version"><small>CURRENT REPRESENTATION</small><strong>${escapeHtml(currentVersion?.version_id ?? replay.trace.agent_version)}</strong><span>trace format v${replay.trace.format_version} · ${abstractions.language_operators.length} compositional operators · utility ${currentVersion?.utility.toFixed(1) ?? "0.0"}</span></div>
    <div><h3>Observed predicate vocabulary</h3><div class="chips">${predicates.map((item) => `<code>${escapeHtml(item)}</code>`).join("") || "<span class='empty'>No predicates observed.</span>"}</div></div>
    ${abstractions.language_operators.map((operator) => `<article class="language-operator"><div><small>COMPILED OPERATOR</small><strong>${escapeHtml(operator.signature)}</strong></div><code>${escapeHtml(operator.algebra)}</code><p>Replaces ${operator.replaces.map(escapeHtml).join(", ")} · ${operator.support} support · ${operator.raw_description_length} → ${operator.compiled_description_length} units · +${operator.utility.toFixed(1)} utility</p></article>`).join("")}
    <div class="language-timeline">${abstractions.language_history.map((version, index) => `<div class="language-history"><span class="${index === abstractions.language_history.length - 1 ? "current" : ""}"></span><article><small>${index === abstractions.language_history.length - 1 ? "ACTIVE" : "ANCESTOR"}</small><strong>${escapeHtml(version.version_id)}</strong><p>${version.operators.length ? `${version.operators.length} operators from ${version.evidence.length} evidence schemas` : "Primitive typed atom language."}</p></article></div>`).join("")}</div>
  </div>`;
}

function objectInspector(step: ReplayStep): string {
  return `
    <div class="panel-head"><div><span class="eyebrow">PERCEPTION</span><h2>Objects & facts</h2></div><span class="object-count">${step.scene.objects.length}</span></div>
    <div class="object-list">${step.scene.objects.map((object) => `
      <div class="object-row">
        <span class="swatch" style="background:${COLORS[object.color] ?? "#fff"}"></span>
        <div><strong>${escapeHtml(object.object_id)}</strong><small>color ${object.color} · area ${object.area}</small></div>
        <code>[${object.bbox.join(",")}]</code>
        <span>@ ${object.centroid.join(",")}</span>
      </div>
    `).join("") || `<div class="empty">No connected foreground objects.</div>`}</div>
    <details class="facts" open><summary>Derived facts <span>${step.scene.facts.length}</span></summary><div class="chips">${step.scene.facts.map((fact) => `<code>${escapeHtml(fact)}</code>`).join("")}</div></details>
  `;
}

function populationView(): string {
  return `
    <div class="panel-head">
      <div><span class="eyebrow">PHYLOGENY</span><h2>Population laboratory</h2></div>
      <label class="experiment-select">EXPERIMENT
        <select id="experiment-select">
          <option value="">${manifests.length ? "Select a manifest" : "No SQLite experiments attached"}</option>
          ${manifests.map((item) => `<option value="${escapeHtml(item.experiment_id)}" ${experiment?.manifest.experiment_id === item.experiment_id ? "selected" : ""}>${escapeHtml(item.name)} · ${item.candidate_count}</option>`).join("")}
        </select>
      </label>
    </div>
    ${experiment ? experimentBody(experiment) : `<div class="population-empty"><div class="orbit"><i></i><i></i><i></i></div><div><strong>${manifests.length ? "Select an experiment manifest" : "Attach an experiment database"}</strong><p>${manifests.length ? "The local database is connected. Choose a manifest above to reconstruct its genealogy, regressions, structural diffs, and Pareto front." : "Start the server with"} ${manifests.length ? "" : "<code>reflector web TRACE --db experiments.sqlite</code> to inspect genealogy, regression evidence, structural diffs, and the Pareto front."}</p></div></div>`}
  `;
}

function experimentBody(report: ExperimentReport): string {
  const chosen = report.candidates.find((item) => item.candidate.candidate_id === selectedCandidate) ?? report.candidates[0];
  if (chosen && !selectedCandidate) selectedCandidate = chosen.candidate.candidate_id;
  return `
    <div class="population-grid">
      <div>
        <h3>Agent genealogy</h3>
        ${genealogy(report, chosen?.candidate.candidate_id ?? null)}
      </div>
      <div>
        <h3>Pareto frontier</h3>
        ${paretoPlot(report.candidates, chosen?.candidate.candidate_id ?? null)}
      </div>
      <div class="leaderboard">
        <h3>Candidate leaderboard</h3>
        ${candidateTable(report.candidates, chosen?.candidate.candidate_id ?? null)}
      </div>
      <div class="candidate-inspector">
        <h3>Structural diff & regression</h3>
        ${chosen ? candidateInspector(chosen, report.candidates) : ""}
      </div>
    </div>
  `;
}

function genealogy(report: ExperimentReport, chosen: string | null): string {
  const generations = Math.max(...report.candidates.map((item) => item.candidate.generation), 0) + 1;
  const width = 500; const height = 210;
  const positions = new Map(report.candidates.map((item, index) => {
    const peers = report.candidates.filter((other) => other.candidate.generation === item.candidate.generation);
    const peer = peers.findIndex((other) => other.candidate.candidate_id === item.candidate.candidate_id);
    return [item.candidate.candidate_id, {
      x: 45 + item.candidate.generation * (410 / Math.max(1, generations - 1)),
      y: 35 + peer * (140 / Math.max(1, peers.length - 1)),
    }] as const;
  }));
  return `<svg class="genealogy" viewBox="0 0 ${width} ${height}">
    ${report.lineage_edges.map((edge) => {
      const a = positions.get(edge.source); const b = positions.get(edge.target);
      return a && b ? `<path d="M${a.x},${a.y} C${a.x + 70},${a.y} ${b.x - 70},${b.y} ${b.x},${b.y}"></path>` : "";
    }).join("")}
    ${report.candidates.map((item) => {
      const point = positions.get(item.candidate.candidate_id)!;
      return `<g class="candidate-node ${item.pareto ? "pareto" : ""} ${chosen === item.candidate.candidate_id ? "selected" : ""}" transform="translate(${point.x} ${point.y})" data-candidate="${item.candidate.candidate_id}"><circle r="10"></circle><text y="27" text-anchor="middle">g${item.candidate.generation}</text><title>${escapeHtml(item.candidate.rationale)}</title></g>`;
    }).join("")}
  </svg>`;
}

function paretoPlot(candidates: CandidateRecord[], chosen: string | null): string {
  const measured = candidates.filter((item) => item.fitness);
  if (!measured.length) return emptyState("No evaluated candidates", "");
  const maxX = Math.max(...measured.map((item) => item.fitness!.planner_expansions), 1);
  return `<div class="pareto-chart">
    <div class="axis-y">REPLAY RETENTION</div>
    <svg viewBox="0 0 500 210">
      <line class="axis" x1="35" y1="10" x2="35" y2="180"></line><line class="axis" x1="35" y1="180" x2="485" y2="180"></line>
      ${measured.map((item) => {
        const x = 35 + item.fitness!.planner_expansions / maxX * 430;
        const y = 180 - item.fitness!.deterministic_replay_rate * 160;
        return `<circle class="pareto-point ${item.pareto ? "front" : ""} ${chosen === item.candidate.candidate_id ? "selected" : ""}" cx="${x}" cy="${y}" r="${item.pareto ? 7 : 5}" data-candidate="${item.candidate.candidate_id}"><title>${short(item.candidate.candidate_id)} · ${percent(item.fitness!.deterministic_replay_rate)}</title></circle>`;
      }).join("")}
      <text x="250" y="205">PLANNER EXPANSIONS →</text>
    </svg>
  </div>`;
}

function candidateTable(candidates: CandidateRecord[], chosen: string | null): string {
  return `<div class="candidate-table">
    <div class="candidate-head"><span>AGENT</span><span>LEVELS</span><span>REPLAY</span><span>WORK</span></div>
    ${candidates.map((item) => `<button class="${chosen === item.candidate.candidate_id ? "selected" : ""}" data-candidate="${item.candidate.candidate_id}">
      <span><i class="${item.pareto ? "on-front" : ""}"></i>${short(item.candidate.candidate_id, 18)}</span>
      <strong>${item.fitness?.levels_advanced ?? "—"}</strong>
      <strong>${item.fitness ? percent(item.fitness.deterministic_replay_rate) : "—"}</strong>
      <strong>${item.fitness?.planner_expansions ?? "—"}</strong>
    </button>`).join("")}
  </div>`;
}

function candidateInspector(item: CandidateRecord, all: CandidateRecord[]): string {
  const parent = all.find((other) => other.candidate.candidate_id === item.candidate.parent_id);
  const keys = Object.keys(item.candidate.config);
  const changes = keys.filter((key) => parent && parent.candidate.config[key] !== item.candidate.config[key]);
  return `<div class="candidate-detail">
    <div class="candidate-title"><span class="${item.pareto ? "pareto-badge" : ""}">${item.pareto ? "PARETO" : `GEN ${item.candidate.generation}`}</span><strong>${short(item.candidate.candidate_id, 28)}</strong></div>
    <p>${escapeHtml(item.candidate.rationale)} <code>via ${escapeHtml(item.candidate.mutation_source)}</code></p>
    <div class="diff">${parent ? (changes.map((key) => `<div><code>${escapeHtml(key)}</code><del>${escapeHtml(parent.candidate.config[key])}</del><ins>${escapeHtml(item.candidate.config[key])}</ins></div>`).join("") || `<span class="empty">No structural configuration change.</span>`) : `<span class="empty">Root genome; no parent diff.</span>`}</div>
    <div class="regression"><small>REGRESSION RETENTION</small><strong>${item.fitness ? percent(item.fitness.deterministic_replay_rate) : "not evaluated"}</strong><span>${item.fitness?.schema_description_length ?? "—"} description units · ${item.fitness?.abstraction_description_savings ?? 0} compiled savings · ${item.fitness?.mean_schema_reliability ? percent(item.fitness.mean_schema_reliability) : "0%"} reliability</span></div>
  </div>`;
}

function emptyState(title: string, text: string): string {
  return `<div class="empty-state"><span>◇</span><strong>${escapeHtml(title)}</strong><p>${escapeHtml(text)}</p></div>`;
}

function drawBoard(): void {
  const canvas = document.querySelector<HTMLCanvasElement>("#board");
  const step = replay.steps[current];
  if (!canvas || !step) return;
  const frame = step.observation.frame;
  const width = frame[0]?.length ?? 0;
  const height = frame.length;
  const box = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(box.width * ratio);
  canvas.height = Math.round(box.height * ratio);
  const context = canvas.getContext("2d");
  if (!context) return;
  context.scale(ratio, ratio);
  context.fillStyle = "#050609";
  context.fillRect(0, 0, box.width, box.height);
  if (!width || !height) return;
  const cell = Math.min((box.width - 32) / width, (box.height - 32) / height);
  const originX = (box.width - cell * width) / 2;
  const originY = (box.height - cell * height) / 2;
  frame.forEach((row, y) => row.forEach((color, x) => {
    context.fillStyle = COLORS[color] ?? "#ffffff";
    context.fillRect(originX + x * cell, originY + y * cell, Math.ceil(cell), Math.ceil(cell));
  }));
  if (cell > 7) {
    context.strokeStyle = "rgba(255,255,255,.055)";
    context.lineWidth = 1;
    for (let x = 0; x <= width; x += 1) {
      context.beginPath(); context.moveTo(originX + x * cell, originY); context.lineTo(originX + x * cell, originY + height * cell); context.stroke();
    }
    for (let y = 0; y <= height; y += 1) {
      context.beginPath(); context.moveTo(originX, originY + y * cell); context.lineTo(originX + width * cell, originY + y * cell); context.stroke();
    }
  }
}

function bind(): void {
  document.querySelectorAll<HTMLElement>("[data-control]").forEach((button) => button.addEventListener("click", () => {
    const control = button.dataset.control;
    if (control === "play") togglePlay();
    else {
      stop();
      if (control === "first") current = 0;
      if (control === "prev") current = Math.max(0, current - 1);
      if (control === "next") current = Math.min(replay.steps.length - 1, current + 1);
      if (control === "last") current = replay.steps.length - 1;
      render();
    }
  }));
  document.querySelectorAll<HTMLElement>("[data-step]").forEach((node) => node.addEventListener("click", () => {
    stop(); current = Number(node.dataset.step); render();
  }));
  document.querySelectorAll<HTMLElement>("[data-tab]").forEach((tab) => tab.addEventListener("click", () => {
    activeModelTab = tab.dataset.tab ?? "concepts"; render();
  }));
  document.querySelector<HTMLSelectElement>("#speed")?.addEventListener("change", (event) => {
    speed = Number((event.target as HTMLSelectElement).value);
    if (playing) { stop(); togglePlay(); }
  });
  document.querySelector<HTMLButtonElement>("#run-branch")?.addEventListener("click", runBranch);
  document.querySelector<HTMLSelectElement>("#experiment-select")?.addEventListener("change", async (event) => {
    const id = (event.target as HTMLSelectElement).value;
    experiment = id ? await api<ExperimentReport>(`/api/experiments/${encodeURIComponent(id)}`) : null;
    selectedCandidate = null; render();
  });
  document.querySelectorAll<HTMLElement>("[data-candidate]").forEach((node) => node.addEventListener("click", () => {
    selectedCandidate = node.dataset.candidate ?? null; render();
  }));
  window.addEventListener("resize", drawBoard, { once: true });
}

async function runBranch(): Promise<void> {
  const information = Number(document.querySelector<HTMLInputElement>("#branch-information")?.value);
  const budget = Number(document.querySelector<HTMLInputElement>("#branch-budget")?.value);
  try {
    branch = await api<BranchReport>("/api/branch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_step: current, patch: { information_weight: information, planner_max_expansions: budget } }),
    });
    render();
  } catch (error) {
    alert(error instanceof Error ? error.message : String(error));
  }
}

function togglePlay(): void {
  if (playing) { stop(); render(); return; }
  playing = true;
  render();
  timer = window.setInterval(() => {
    if (current >= replay.steps.length - 1) { stop(); render(); return; }
    current += 1; render();
  }, 900 / speed);
}

function stop(): void {
  playing = false;
  if (timer !== undefined) window.clearInterval(timer);
  timer = undefined;
}

function render(): void {
  app.innerHTML = shell();
  drawBoard();
  bind();
}

async function start(): Promise<void> {
  try {
    [replay, { experiments: manifests }] = await Promise.all([
      api<Replay>("/api/replay"),
      api<{ experiments: Manifest[] }>("/api/experiments"),
    ]);
    render();
  } catch (error) {
    app.innerHTML = `<main class="fatal"><span>R</span><h1>Replay unavailable</h1><p>${escapeHtml(error instanceof Error ? error.message : error)}</p><code>reflector web TRACE [--db EXPERIMENTS.sqlite]</code></main>`;
  }
}

document.addEventListener("keydown", (event) => {
  if (!replay) return;
  if (event.key === " ") { event.preventDefault(); togglePlay(); }
  if (event.key === "ArrowRight") { stop(); current = Math.min(replay.steps.length - 1, current + 1); render(); }
  if (event.key === "ArrowLeft") { stop(); current = Math.max(0, current - 1); render(); }
});

void start();
