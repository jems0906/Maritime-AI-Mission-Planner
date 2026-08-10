import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { AuditPanel } from "./components/AuditPanel";
import { GridMap } from "./components/GridMap";
import { MigrationStatusCard } from "./components/MigrationStatusCard";
import { RecommendationTable } from "./components/RecommendationTable";
import { ReportCard } from "./components/ReportCard";
import { AuditLog, MigrationStatus, Recommendation, Report, Scenario, Sector } from "./types/mission";

type UploadPayload = {
  rows: number;
  cols: number;
  sectors: Array<{
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
  }>;
};

type ReviewDraft = {
  action: "accept" | "reject" | "override";
  overrideRank?: number;
  justification: string;
};

export function App() {
  const runtimeModeLabel = import.meta.env.DEV ? "Vite React Mode" : "Vite Build Mode";
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(null);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLog[]>([]);
  const [reviewerName, setReviewerName] = useState("Ops Officer");
  const [reviewDrafts, setReviewDrafts] = useState<Record<number, ReviewDraft>>({});
  const [selectedSectorId, setSelectedSectorId] = useState<number | null>(null);
  const [modelUsed, setModelUsed] = useState("-");
  const [migrationStatus, setMigrationStatus] = useState<MigrationStatus | null>(null);
  const [migrationError, setMigrationError] = useState("");
  const [migrationLoading, setMigrationLoading] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");

  const [generateForm, setGenerateForm] = useState({ name: "Synthetic Mission Alpha", rows: 8, cols: 8, seed: 7 });

  const sectorsById = useMemo(() => new Map<number, Sector>(sectors.map((sector) => [sector.id, sector])), [sectors]);

  useEffect(() => {
    void refreshScenarios();
    void refreshMigrationStatus();
  }, []);

  async function refreshMigrationStatus() {
    try {
      setMigrationLoading(true);
      setMigrationError("");
      const status = await api.getMigrationStatus();
      setMigrationStatus(status);
    } catch (err) {
      setMigrationStatus(null);
      setMigrationError((err as Error).message);
    } finally {
      setMigrationLoading(false);
    }
  }

  async function refreshScenarios() {
    try {
      setError("");
      const items = await api.listScenarios();
      setScenarios(items);
      if (!selectedScenarioId && items.length > 0) {
        await loadScenario(items[0].id);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadScenario(scenarioId: number) {
    try {
      setError("");
      setSelectedScenarioId(scenarioId);
      const [detail, recs, logs] = await Promise.all([
        api.getScenario(scenarioId),
        api.listRecommendations(scenarioId),
        api.getAuditLog(scenarioId)
      ]);
      setSectors(detail.sectors);
      setRecommendations(recs);
      setAuditLog(logs);
      setSelectedSectorId(detail.sectors[0]?.id ?? null);
      setReviewDrafts({});

      if (recs.length > 0) {
        const scenarioReport = await api.getReport(scenarioId);
        setReport(scenarioReport);
      } else {
        setReport(null);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onGenerateScenario() {
    try {
      setError("");
      setMessage("");
      const scenario = await api.generateScenario({
        name: generateForm.name,
        rows: generateForm.rows,
        cols: generateForm.cols,
        seed: generateForm.seed
      });
      await refreshScenarios();
      await loadScenario(scenario.id);
      setMessage(`Generated scenario ${scenario.name}`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onUploadScenario(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      setError("");
      const text = await file.text();
      const payload = JSON.parse(text) as UploadPayload;
      const scenario = await api.uploadScenario({
        name: `${file.name.replace(".json", "")}`,
        rows: payload.rows,
        cols: payload.cols,
        sectors: payload.sectors
      });
      await refreshScenarios();
      await loadScenario(scenario.id);
      setMessage(`Uploaded scenario from ${file.name}`);
    } catch (err) {
      setError(`Upload failed: ${(err as Error).message}`);
    }
  }

  async function onUploadScenarioCsv(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      setError("");
      const scenario = await api.uploadScenarioCsv({
        name: file.name.replace(".csv", ""),
        rows: generateForm.rows,
        cols: generateForm.cols,
        file
      });
      await refreshScenarios();
      await loadScenario(scenario.id);
      setMessage(`Uploaded CSV scenario from ${file.name}`);
    } catch (err) {
      setError(`CSV upload failed: ${(err as Error).message}`);
    }
  }

  async function onRankScenario() {
    if (!selectedScenarioId) {
      return;
    }
    try {
      setError("");
      const result = await api.rankScenario(selectedScenarioId);
      setRecommendations(result.recommendations);
      setModelUsed(result.model_used);
      const [scenarioReport, logs] = await Promise.all([
        api.getReport(selectedScenarioId),
        api.getAuditLog(selectedScenarioId)
      ]);
      setReport(scenarioReport);
      setAuditLog(logs);
      setMessage(`Generated ${result.recommendations.length} ranked recommendations`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onTrainModel() {
    if (!selectedScenarioId) {
      return;
    }
    try {
      setError("");
      const result = await api.trainModel(selectedScenarioId);
      setMessage(`${result.message} using ${result.samples} samples`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onSubmitReview(recommendationId: number) {
    if (!selectedScenarioId) {
      return;
    }
    const draft = reviewDrafts[recommendationId];
    if (!draft || !draft.justification.trim()) {
      setError("A justification is required for every review decision.");
      return;
    }

    try {
      setError("");
      await api.reviewRecommendation(recommendationId, {
        reviewer_name: reviewerName,
        action: draft.action,
        override_rank: draft.overrideRank,
        justification: draft.justification
      });
      const [recs, scenarioReport, logs] = await Promise.all([
        api.listRecommendations(selectedScenarioId),
        api.getReport(selectedScenarioId),
        api.getAuditLog(selectedScenarioId)
      ]);
      setRecommendations(recs);
      setReport(scenarioReport);
      setAuditLog(logs);
      setMessage("Review decision recorded in audit history.");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onExportReportMarkdown() {
    if (!selectedScenarioId) {
      return;
    }
    try {
      setError("");
      const markdown = await api.getReportMarkdown(selectedScenarioId);
      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `scenario-${selectedScenarioId}-after-action-report.md`;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("Downloaded after-action report markdown.");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <h1>Maritime Search Decision Support</h1>
        <p>
          Recommendation-only workflow for synthetic maritime missions. AI priorities are advisory and every final tasking
          decision must be approved by a human operator.
        </p>
      </header>

      <section className="warning-banner">
        This system does not autonomously assign missions. Human review, acceptance/rejection, and justification are
        mandatory for every recommendation.
      </section>

      <section className="runtime-banner" aria-label="runtime-mode">
        <strong>Runtime:</strong> {runtimeModeLabel}
        <span>Switch to fallback mode with frontend npm run dev when native bundler binaries are blocked.</span>
      </section>

      <section className="card controls">
        <h3>Scenario Data</h3>
        <div className="control-grid">
          <label>
            Mission name
            <input
              value={generateForm.name}
              onChange={(event) => setGenerateForm((prev) => ({ ...prev, name: event.target.value }))}
            />
          </label>

          <label>
            Rows
            <input
              type="number"
              min={2}
              max={50}
              value={generateForm.rows}
              onChange={(event) => setGenerateForm((prev) => ({ ...prev, rows: Number(event.target.value) }))}
            />
          </label>

          <label>
            Columns
            <input
              type="number"
              min={2}
              max={50}
              value={generateForm.cols}
              onChange={(event) => setGenerateForm((prev) => ({ ...prev, cols: Number(event.target.value) }))}
            />
          </label>

          <label>
            Seed
            <input
              type="number"
              value={generateForm.seed}
              onChange={(event) => setGenerateForm((prev) => ({ ...prev, seed: Number(event.target.value) }))}
            />
          </label>

          <div className="button-row">
            <button onClick={onGenerateScenario}>Generate Synthetic Scenario</button>
            <label className="file-upload">
              Upload Scenario JSON
              <input type="file" accept=".json" onChange={onUploadScenario} />
            </label>
            <label className="file-upload alt">
              Upload Scenario CSV
              <input type="file" accept=".csv" onChange={onUploadScenarioCsv} />
            </label>
          </div>
        </div>
      </section>

      <section className="card controls">
        <h3>Mission Execution</h3>
        <div className="button-row">
          <select
            value={selectedScenarioId ?? ""}
            onChange={(event) => {
              const nextId = Number(event.target.value);
              if (nextId) {
                void loadScenario(nextId);
              }
            }}
          >
            <option value="">Select scenario</option>
            {scenarios.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.name} ({scenario.grid_rows}x{scenario.grid_cols})
              </option>
            ))}
          </select>

          <button disabled={!selectedScenarioId} onClick={onTrainModel}>
            Train / Refresh ML Model
          </button>

          <button disabled={!selectedScenarioId} onClick={onRankScenario}>
            Rank Search Areas
          </button>

          <input
            placeholder="Reviewer name"
            value={reviewerName}
            onChange={(event) => setReviewerName(event.target.value)}
          />
        </div>
        <div className="muted">Current ranking method: {modelUsed}</div>
      </section>

      {message && <section className="toast success">{message}</section>}
      {error && <section className="toast error">{error}</section>}

      <section className="layout-grid">
        <div className="card">
          <h3>Interactive Grid Risk View</h3>
          <GridMap
            sectors={sectors}
            recommendations={recommendations}
            selectedSectorId={selectedSectorId}
            onSelectSector={setSelectedSectorId}
          />
        </div>

        <ReportCard report={report} onExportMarkdown={onExportReportMarkdown} />
      </section>

      <MigrationStatusCard
        status={migrationStatus}
        error={migrationError}
        loading={migrationLoading}
        onRefresh={() => {
          void refreshMigrationStatus();
        }}
      />

      <RecommendationTable
        recommendations={recommendations}
        sectorsById={sectorsById}
        reviewerName={reviewerName}
        draftByRecommendation={reviewDrafts}
        onDraftChange={(recommendationId, next) =>
          setReviewDrafts((prev) => ({
            ...prev,
            [recommendationId]: next
          }))
        }
        onSubmitReview={onSubmitReview}
        selectedSectorId={selectedSectorId}
        onSelectSector={setSelectedSectorId}
      />

      <AuditPanel logs={auditLog} />
    </div>
  );
}
