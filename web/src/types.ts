export type Primitive = string | number | boolean | null;
export type Json = Primitive | Json[] | { [key: string]: Json };

export interface Observation {
  state: string;
  available_actions: number[];
  frame: number[][];
  levels_completed: number;
}

export interface Decision {
  action_id: number;
  data: Record<string, number>;
  reason: string;
}

export interface SceneObject {
  object_id: string;
  color: number;
  area: number;
  bbox: [number, number, number, number];
  centroid: [number, number];
}

export interface Scene {
  index: number;
  state: string;
  levels_completed: number;
  available_actions: number[];
  objects: SceneObject[];
  facts: string[];
  frame_digest: string;
}

export interface Schema {
  schema_id: string;
  context: string[];
  action_id: number;
  result: string[];
  support: number;
  opportunities: number;
  confirmations: number;
  reliability: number;
  attribution: number;
}

export interface Concept {
  concept_id: string;
  name: string;
  kind: string;
  definition: string[];
  evidence: string[];
  support: number;
  utility: number;
  complexity: number;
  counterfactual_savings: number;
}

export interface Hypothesis {
  hypothesis_id: string;
  action_id?: number;
  effect?: string;
  antecedent?: string;
  consequent?: string;
  support: number;
  confidence: number;
  strength?: number;
}

export interface Graph {
  nodes: { id: string; kind: string }[];
  edges: { source: string; relation: string; target: string }[];
}

export interface SymbolicState {
  schemas: { schemas: Schema[]; action_trials: Record<string, number> };
  concepts: { concepts: Concept[] };
  hypotheses: { causal: Hypothesis[]; temporal: Hypothesis[] };
  last_experiment: Record<string, Json> | null;
  last_plan: {
    actions: number[];
    predicted_events: string[];
    confidence: number;
    expansions: number;
  } | null;
  planner_expansions: number;
  dependency_graph: Graph;
}

export interface ReplayStep {
  index: number;
  observation: Observation;
  scene: Scene;
  recorded_decision: Decision;
  replayed_decision: Decision;
  decision_matches: boolean;
  incoming_transition: {
    action_id: number;
    result: string[];
    context: string[];
  } | null;
  predictions: { event: string; probability: number }[];
  new_concepts: string[];
  new_hypotheses: string[];
  experiment: string | null;
  plan_actions: number[];
  planner_expansions: number;
  symbolic_state: SymbolicState;
}

export interface Replay {
  trace: {
    format_version: number;
    agent_version: string;
    step_count: number;
    terminal: {
      observation: Observation;
      scene: Scene | null;
      transition: { result: string[] } | null;
    } | null;
  };
  config: Record<string, boolean | number>;
  steps: ReplayStep[];
  final_symbolic_state: SymbolicState;
}

export interface Manifest {
  experiment_id: string;
  name: string;
  seed: number;
  trace_hashes: Record<string, string>;
  holdout_seeds: number[];
  agent_version: string;
  created_at: string;
  candidate_count: number;
}

export interface CandidateRecord {
  candidate: {
    candidate_id: string;
    config: Record<string, boolean | number>;
    parent_id: string | null;
    generation: number;
    rationale: string;
  };
  fitness: {
    levels_advanced: number;
    deterministic_replay_rate: number;
    mean_schema_reliability: number;
    planner_expansions: number;
    schema_description_length: number;
  } | null;
  details: Record<string, Json> | null;
  pareto: boolean;
}

export interface ExperimentReport {
  manifest: Manifest;
  candidates: CandidateRecord[];
  lineage_edges: { source: string; target: string }[];
}

export interface BranchReport {
  mode: string;
  limitation: string;
  from_step: number;
  divergences: number;
  config: Record<string, boolean | number>;
  steps: ReplayStep[];
}
