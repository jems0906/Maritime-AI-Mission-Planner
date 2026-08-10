import { AuditLog, MigrationStatus, Recommendation, Report, Scenario, ScenarioDetail } from "../types/mission";

type UploadSector = {
  sector_code: string;
  row_idx: number;
  col_idx: number;
  weather_score: number;
  sea_state: number;
  sensor_confidence: number;
  elapsed_search_minutes: number;
  reported_anomalies: number;
  coverage_ratio: number;
  has_ground_truth_anomaly?: boolean;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const OPERATOR_KEY = import.meta.env.VITE_OPERATOR_API_KEY;
const REVIEWER_KEY = import.meta.env.VITE_REVIEWER_API_KEY;
const ADMIN_KEY = import.meta.env.VITE_ADMIN_API_KEY;

function withAuthHeader(init: RequestInit | undefined, keyName: string, keyValue?: string): RequestInit | undefined {
  if (!keyValue) {
    return init;
  }
  const baseHeaders = (init?.headers ?? {}) as Record<string, string>;
  return {
    ...(init ?? {}),
    headers: {
      ...baseHeaders,
      [keyName]: keyValue
    }
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    ...(init ?? {}),
    headers: isFormData
      ? init?.headers
      : {
          "Content-Type": "application/json",
          ...(init?.headers ?? {})
        }
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail ?? "Request failed");
  }

  return response.json() as Promise<T>;
}

async function requestText(path: string, init?: RequestInit): Promise<string> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }
  return response.text();
}

export const api = {
  listScenarios: () => request<Scenario[]>("/scenarios"),
  getScenario: (scenarioId: number) => request<ScenarioDetail>(`/scenarios/${scenarioId}`),
  generateScenario: (payload: { name: string; rows: number; cols: number; seed?: number }) =>
    request<Scenario>(
      "/scenarios/generate",
      withAuthHeader(
        {
          method: "POST",
          body: JSON.stringify(payload)
        },
        "X-Operator-Key",
        OPERATOR_KEY
      )
    ),
  uploadScenario: (payload: { name: string; rows: number; cols: number; sectors: UploadSector[] }) =>
    request<Scenario>(
      "/scenarios/upload",
      withAuthHeader(
        {
          method: "POST",
          body: JSON.stringify(payload)
        },
        "X-Operator-Key",
        OPERATOR_KEY
      )
    ),
  uploadScenarioCsv: (payload: { name: string; rows: number; cols: number; file: File }) => {
    const form = new FormData();
    form.append("name", payload.name);
    form.append("rows", String(payload.rows));
    form.append("cols", String(payload.cols));
    form.append("file", payload.file);
    return request<Scenario>(
      "/scenarios/upload-csv",
      withAuthHeader(
        {
          method: "POST",
          body: form
        },
        "X-Operator-Key",
        OPERATOR_KEY
      )
    );
  },
  rankScenario: (scenarioId: number) =>
    request<{ scenario_id: number; recommendations: Recommendation[]; model_used: string }>(`/scenarios/${scenarioId}/rank`,
      withAuthHeader(
        { method: "POST" },
        "X-Operator-Key",
        OPERATOR_KEY
      )
    ),
  listRecommendations: (scenarioId: number) => request<Recommendation[]>(`/scenarios/${scenarioId}/recommendations`),
  reviewRecommendation: (
    recommendationId: number,
    payload: { reviewer_name: string; action: "accept" | "reject" | "override"; override_rank?: number; justification: string }
  ) =>
    request(
      `/recommendations/${recommendationId}/review`,
      withAuthHeader(
        {
          method: "POST",
          body: JSON.stringify(payload)
        },
        "X-Reviewer-Key",
        REVIEWER_KEY
      )
    ),
  trainModel: (scenarioId?: number) =>
    request<{ message: string; samples: number }>(
      "/admin/train",
      withAuthHeader(
        {
          method: "POST",
          body: JSON.stringify({ scenario_id: scenarioId })
        },
        "X-Admin-Key",
        ADMIN_KEY
      )
    ),
  getMigrationStatus: () =>
    request<MigrationStatus>(
      "/system/migration-status",
      withAuthHeader(
        {
          method: "GET"
        },
        "X-Admin-Key",
        ADMIN_KEY
      )
    ),
  getReport: (scenarioId: number) => request<Report>(`/scenarios/${scenarioId}/report`),
  getReportMarkdown: (scenarioId: number) => requestText(`/scenarios/${scenarioId}/report.md`),
  getAuditLog: (scenarioId: number) => request<AuditLog[]>(`/scenarios/${scenarioId}/audit`)
};
