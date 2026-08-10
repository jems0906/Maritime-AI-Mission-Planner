export type Scenario = {
  id: number;
  name: string;
  grid_rows: number;
  grid_cols: number;
  created_at: string;
};

export type Sector = {
  id: number;
  scenario_id: number;
  sector_code: string;
  row_idx: number;
  col_idx: number;
  weather_score: number;
  sea_state: number;
  sensor_confidence: number;
  elapsed_search_minutes: number;
  reported_anomalies: number;
  coverage_ratio: number;
  has_ground_truth_anomaly: boolean;
};

export type Recommendation = {
  id: number;
  scenario_id: number;
  sector_id: number;
  priority_rank: number;
  risk_score: number;
  model_confidence: number;
  explanation: {
    top_factors: Array<{
      feature: string;
      contribution: number;
      direction: "increases" | "decreases";
    }>;
    coverage_status: "incomplete" | "adequate";
    method: string;
  };
  status: "pending" | "accept" | "reject" | "override";
  created_at: string;
};

export type ScenarioDetail = {
  scenario: Scenario;
  sectors: Sector[];
};

export type Report = {
  scenario_id: number;
  mission_coverage_percent: number;
  reviewed_count: number;
  pending_count: number;
  accepted_count: number;
  rejected_count: number;
  overridden_count: number;
  model_precision_at_25: number;
  model_recall_at_25: number;
  human_override_rate: number;
  improvement_recommendations: string[];
};

export type AuditLog = {
  id: number;
  scenario_id: number | null;
  recommendation_id: number | null;
  actor: string;
  action_type: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type MigrationStatus = {
  current_revision: string | null;
  head_revision: string | null;
  is_up_to_date: boolean;
};
