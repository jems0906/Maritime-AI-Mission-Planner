const API_BASE = "/api";
const RUNTIME_MODE = "Fallback Static Mode";
const operatorKey = window.localStorage.getItem("operatorKey") || "operator-secret";
const reviewerKey = window.localStorage.getItem("reviewerKey") || "reviewer-secret";
const adminKey = window.localStorage.getItem("adminKey") || "admin-secret";

const state = {
  scenarios: [],
  selectedScenarioId: null,
  sectors: [],
  recommendations: [],
  auditLog: [],
  report: null,
  modelUsed: "-",
  selectedSectorId: null
};

const el = {
  missionName: document.getElementById("mission-name"),
  rows: document.getElementById("rows"),
  cols: document.getElementById("cols"),
  seed: document.getElementById("seed"),
  scenarioSelect: document.getElementById("scenario-select"),
  reviewerName: document.getElementById("reviewer-name"),
  modelUsed: document.getElementById("model-used"),
  report: document.getElementById("report"),
  recommendationsBody: document.getElementById("recommendations-body"),
  auditLog: document.getElementById("audit-log"),
  migrationStatus: document.getElementById("migration-status"),
  success: document.getElementById("toast-success"),
  error: document.getElementById("toast-error"),
  runtimeModeLabel: document.getElementById("runtime-mode-label"),
  runtimeModeHelp: document.getElementById("runtime-mode-help")
};

if (el.runtimeModeLabel) {
  el.runtimeModeLabel.textContent = `Runtime: ${RUNTIME_MODE}`;
}
if (el.runtimeModeHelp) {
  el.runtimeModeHelp.textContent = "Use npm run dev:vite for Vite React mode when native bundler binaries are available.";
}

const map = L.map("map").setView([20, -30], 3);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 8,
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);
let mapLayerGroup = L.layerGroup().addTo(map);

function showToast(type, message) {
  if (type === "success") {
    el.success.textContent = message;
    el.success.classList.remove("hidden");
    el.error.classList.add("hidden");
  } else {
    el.error.textContent = message;
    el.error.classList.remove("hidden");
    el.success.classList.add("hidden");
  }
}

function toJsonSafe(value) {
  return JSON.stringify(value).replace(/[<>]/g, "");
}

async function request(path, init = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init.headers || {})
    }
  });

  if (!response.ok) {
    const payload = await response.text();
    throw new Error(payload || "Request failed");
  }

  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

function coverageStatusForRecommendation(rec) {
  return rec?.explanation?.coverage_status || "unknown";
}

function renderMap() {
  mapLayerGroup.clearLayers();

  if (!state.sectors.length) {
    return;
  }

  const maxRow = Math.max(...state.sectors.map((s) => s.row_idx), 1);
  const maxCol = Math.max(...state.sectors.map((s) => s.col_idx), 1);
  const scale = 1.2;
  const baseLat = 15;
  const baseLng = -35;

  state.sectors.forEach((sector) => {
    const rec = state.recommendations.find((r) => r.sector_id === sector.id);
    const rank = rec?.priority_rank ?? 999;
    const risk = rec?.risk_score ?? 0;
    const selected = sector.id === state.selectedSectorId;

    const lat = baseLat + (maxRow - sector.row_idx) * scale;
    const lng = baseLng + sector.col_idx * scale;

    const color = rank <= 3 ? "#b91c1c" : rank <= 10 ? "#ea580c" : "#0369a1";
    const circle = L.circleMarker([lat, lng], {
      radius: selected ? 12 : 9,
      color,
      fillColor: color,
      fillOpacity: 0.7,
      weight: selected ? 3 : 1
    });

    circle.bindPopup(
      `<strong>${sector.sector_code}</strong><br/>Risk: ${risk.toFixed(3)}<br/>Rank: ${rank}<br/>Coverage: ${(sector.coverage_ratio *
        100).toFixed(1)}%`
    );

    circle.on("click", () => {
      state.selectedSectorId = sector.id;
      renderMap();
      renderRecommendations();
    });

    mapLayerGroup.addLayer(circle);
  });
}

function renderReport() {
  if (!state.report) {
    el.report.innerHTML = '<p class="muted">Rank a scenario to view after-action metrics.</p>';
    return;
  }

  const r = state.report;
  el.report.innerHTML = `
    <div><span class="badge">Coverage</span> ${r.mission_coverage_percent.toFixed(1)}%</div>
    <div><span class="badge">Reviewed</span> ${r.reviewed_count} / ${r.reviewed_count + r.pending_count}</div>
    <div><span class="badge">Accepted</span> ${r.accepted_count}</div>
    <div><span class="badge">Rejected</span> ${r.rejected_count}</div>
    <div><span class="badge">Override</span> ${r.overridden_count}</div>
    <div><span class="badge">Precision@25</span> ${r.model_precision_at_25.toFixed(2)}</div>
    <div><span class="badge">Recall@25</span> ${r.model_recall_at_25.toFixed(2)}</div>
    <div><span class="badge">Override rate</span> ${(r.human_override_rate * 100).toFixed(1)}%</div>
  `;
}

function renderAuditLog() {
  if (!state.auditLog.length) {
    el.auditLog.innerHTML = '<p class="muted">No audit entries yet.</p>';
    return;
  }

  el.auditLog.innerHTML = state.auditLog
    .slice()
    .reverse()
    .map(
      (entry) => `
      <div class="audit-item">
        <strong>${entry.actor}</strong> - ${entry.action_type}<br/>
        <small>${new Date(entry.created_at).toLocaleString()}</small><br/>
        <code>${toJsonSafe(entry.details)}</code>
      </div>
    `
    )
    .join("");
}

function renderRecommendations() {
  if (!state.recommendations.length) {
    el.recommendationsBody.innerHTML = '<tr><td colspan="7" class="muted">No recommendations yet.</td></tr>';
    return;
  }

  const reviewerName = el.reviewerName.value.trim() || "Ops Officer";

  el.recommendationsBody.innerHTML = state.recommendations
    .map((rec) => {
      const sector = state.sectors.find((s) => s.id === rec.sector_id);
      const selected = rec.sector_id === state.selectedSectorId ? " style=\"background:#ecfeff;\"" : "";
      const factors = (rec.explanation?.top_factors || [])
        .slice(0, 2)
        .map((f) => `${f.feature}: ${Number(f.contribution).toFixed(2)}`)
        .join("; ");

      return `
        <tr${selected}>
          <td>${rec.priority_rank}</td>
          <td>${sector ? sector.sector_code : rec.sector_id}</td>
          <td>${rec.risk_score.toFixed(3)}</td>
          <td>${rec.model_confidence.toFixed(2)}</td>
          <td>${coverageStatusForRecommendation(rec)}</td>
          <td>${factors || "-"}</td>
          <td>
            <select id="action-${rec.id}">
              <option value="accept">accept</option>
              <option value="reject">reject</option>
              <option value="override">override</option>
            </select>
            <input id="rank-${rec.id}" type="number" min="1" placeholder="override rank" style="width:120px;" />
            <input id="just-${rec.id}" placeholder="justification" style="min-width:220px;" />
            <button data-review="${rec.id}" data-reviewer="${reviewerName}">Submit</button>
          </td>
        </tr>
      `;
    })
    .join("");

  el.recommendationsBody.querySelectorAll("button[data-review]").forEach((button) => {
    button.addEventListener("click", async () => {
      const recommendationId = Number(button.dataset.review);
      const action = document.getElementById(`action-${recommendationId}`).value;
      const overrideRankRaw = document.getElementById(`rank-${recommendationId}`).value;
      const justification = document.getElementById(`just-${recommendationId}`).value.trim();
      const reviewer = el.reviewerName.value.trim() || "Ops Officer";

      if (!justification) {
        showToast("error", "A justification is required for every review decision.");
        return;
      }

      try {
        await request(`/recommendations/${recommendationId}/review`, {
          method: "POST",
          headers: { "X-Reviewer-Key": reviewerKey },
          body: JSON.stringify({
            reviewer_name: reviewer,
            action,
            override_rank: overrideRankRaw ? Number(overrideRankRaw) : undefined,
            justification
          })
        });

        showToast("success", "Review decision recorded in audit history.");
        await refreshScenario(state.selectedScenarioId);
      } catch (error) {
        showToast("error", error.message);
      }
    });
  });
}

function renderScenarioSelect() {
  el.scenarioSelect.innerHTML = [
    '<option value="">Select scenario</option>',
    ...state.scenarios.map(
      (scenario) =>
        `<option value="${scenario.id}" ${scenario.id === state.selectedScenarioId ? "selected" : ""}>${scenario.name} (${scenario.grid_rows}x${
          scenario.grid_cols
        })</option>`
    )
  ].join("");
}

async function refreshMigrationStatus() {
  try {
    const status = await request("/system/migration-status", {
      method: "GET",
      headers: { "X-Admin-Key": adminKey }
    });

    el.migrationStatus.innerHTML = `
      <div>Current revision: <strong>${status.current_revision || "n/a"}</strong></div>
      <div>Head revision: <strong>${status.head_revision || "n/a"}</strong></div>
      <div>Up to date: <strong>${status.is_up_to_date ? "yes" : "no"}</strong></div>
    `;
  } catch (error) {
    el.migrationStatus.textContent = error.message;
  }
}

async function refreshScenario(scenarioId) {
  if (!scenarioId) {
    return;
  }

  const [detail, recommendations, auditLog] = await Promise.all([
    request(`/scenarios/${scenarioId}`),
    request(`/scenarios/${scenarioId}/recommendations`),
    request(`/scenarios/${scenarioId}/audit`)
  ]);

  state.selectedScenarioId = scenarioId;
  state.sectors = detail.sectors;
  state.recommendations = recommendations;
  state.auditLog = auditLog;
  state.selectedSectorId = detail.sectors[0]?.id || null;

  if (state.recommendations.length) {
    state.report = await request(`/scenarios/${scenarioId}/report`);
  } else {
    state.report = null;
  }

  renderScenarioSelect();
  renderMap();
  renderRecommendations();
  renderReport();
  renderAuditLog();
}

async function refreshScenarios(initial = false) {
  state.scenarios = await request("/scenarios");
  if (initial && state.scenarios.length) {
    state.selectedScenarioId = state.scenarios[0].id;
  }

  renderScenarioSelect();

  if (state.selectedScenarioId) {
    await refreshScenario(state.selectedScenarioId);
  }
}

async function generateScenario() {
  const payload = {
    name: el.missionName.value,
    rows: Number(el.rows.value),
    cols: Number(el.cols.value),
    seed: Number(el.seed.value)
  };

  const scenario = await request("/scenarios/generate", {
    method: "POST",
    headers: { "X-Operator-Key": operatorKey },
    body: JSON.stringify(payload)
  });

  showToast("success", `Generated scenario ${scenario.name}`);
  state.selectedScenarioId = scenario.id;
  await refreshScenarios();
}

async function uploadJsonScenario(file) {
  const text = await file.text();
  const json = JSON.parse(text);

  const scenario = await request("/scenarios/upload", {
    method: "POST",
    headers: { "X-Operator-Key": operatorKey },
    body: JSON.stringify({
      name: file.name.replace(/\.json$/i, ""),
      rows: Number(json.rows),
      cols: Number(json.cols),
      sectors: json.sectors
    })
  });

  showToast("success", `Uploaded scenario from ${file.name}`);
  state.selectedScenarioId = scenario.id;
  await refreshScenarios();
}

async function uploadCsvScenario(file) {
  const form = new FormData();
  form.append("name", file.name.replace(/\.csv$/i, ""));
  form.append("rows", String(Number(el.rows.value)));
  form.append("cols", String(Number(el.cols.value)));
  form.append("file", file);

  const scenario = await request("/scenarios/upload-csv", {
    method: "POST",
    headers: { "X-Operator-Key": operatorKey },
    body: form
  });

  showToast("success", `Uploaded CSV scenario from ${file.name}`);
  state.selectedScenarioId = scenario.id;
  await refreshScenarios();
}

async function rankScenario() {
  if (!state.selectedScenarioId) {
    return;
  }

  const result = await request(`/scenarios/${state.selectedScenarioId}/rank`, {
    method: "POST",
    headers: { "X-Operator-Key": operatorKey }
  });

  state.recommendations = result.recommendations;
  state.modelUsed = result.model_used;
  el.modelUsed.textContent = `Current ranking method: ${state.modelUsed}`;

  state.report = await request(`/scenarios/${state.selectedScenarioId}/report`);
  state.auditLog = await request(`/scenarios/${state.selectedScenarioId}/audit`);
  renderMap();
  renderRecommendations();
  renderReport();
  renderAuditLog();

  showToast("success", `Generated ${result.recommendations.length} ranked recommendations`);
}

async function trainModel() {
  if (!state.selectedScenarioId) {
    return;
  }

  const result = await request("/admin/train", {
    method: "POST",
    headers: { "X-Admin-Key": adminKey },
    body: JSON.stringify({ scenario_id: state.selectedScenarioId })
  });

  showToast("success", `${result.message} using ${result.samples} samples`);
}

async function exportReportMarkdown() {
  if (!state.selectedScenarioId) {
    return;
  }

  const markdown = await request(`/scenarios/${state.selectedScenarioId}/report.md`);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `scenario-${state.selectedScenarioId}-after-action-report.md`;
  anchor.click();
  URL.revokeObjectURL(url);

  showToast("success", "Downloaded after-action report markdown.");
}

function bindEvents() {
  document.getElementById("btn-generate").addEventListener("click", () =>
    generateScenario().catch((error) => showToast("error", error.message))
  );

  document.getElementById("btn-train").addEventListener("click", () =>
    trainModel().catch((error) => showToast("error", error.message))
  );

  document.getElementById("btn-rank").addEventListener("click", () =>
    rankScenario().catch((error) => showToast("error", error.message))
  );

  document.getElementById("btn-export-report").addEventListener("click", () =>
    exportReportMarkdown().catch((error) => showToast("error", error.message))
  );

  document.getElementById("btn-refresh-migration").addEventListener("click", () =>
    refreshMigrationStatus().catch((error) => showToast("error", error.message))
  );

  document.getElementById("scenario-select").addEventListener("change", async (event) => {
    const nextId = Number(event.target.value);
    if (nextId) {
      try {
        await refreshScenario(nextId);
      } catch (error) {
        showToast("error", error.message);
      }
    }
  });

  document.getElementById("upload-json").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    uploadJsonScenario(file).catch((error) => showToast("error", `Upload failed: ${error.message}`));
  });

  document.getElementById("upload-csv").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    uploadCsvScenario(file).catch((error) => showToast("error", `CSV upload failed: ${error.message}`));
  });
}

async function bootstrap() {
  bindEvents();
  await Promise.all([refreshScenarios(true), refreshMigrationStatus()]);
}

bootstrap().catch((error) => showToast("error", error.message));
