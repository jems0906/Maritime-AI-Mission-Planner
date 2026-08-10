import { Report } from "../types/mission";

type ReportCardProps = {
  report: Report | null;
  onExportMarkdown?: () => void;
};

export function ReportCard({ report, onExportMarkdown }: ReportCardProps) {
  if (!report) {
    return <div className="card">After-action report is generated when recommendations exist for a scenario.</div>;
  }

  return (
    <div className="card">
      <div className="button-row report-header-row">
        <h3>After-Action Report</h3>
        <button onClick={onExportMarkdown}>Export .md Report</button>
      </div>
      <div className="report-grid">
        <div>
          <strong>Mission Coverage</strong>
          <div>{report.mission_coverage_percent.toFixed(1)}%</div>
        </div>
        <div>
          <strong>Reviewed Recommendations</strong>
          <div>{report.reviewed_count}</div>
        </div>
        <div>
          <strong>Pending Recommendations</strong>
          <div>{report.pending_count}</div>
        </div>
        <div>
          <strong>Model Precision@25%</strong>
          <div>{(report.model_precision_at_25 * 100).toFixed(1)}%</div>
        </div>
        <div>
          <strong>Model Recall@25%</strong>
          <div>{(report.model_recall_at_25 * 100).toFixed(1)}%</div>
        </div>
        <div>
          <strong>Human Override Rate</strong>
          <div>{(report.human_override_rate * 100).toFixed(1)}%</div>
        </div>
      </div>

      <h4>Review Actions</h4>
      <ul>
        <li>Accepted: {report.accepted_count}</li>
        <li>Rejected: {report.rejected_count}</li>
        <li>Overridden: {report.overridden_count}</li>
      </ul>

      <h4>Improvement Recommendations</h4>
      <ul>
        {report.improvement_recommendations.map((rec) => (
          <li key={rec}>{rec}</li>
        ))}
      </ul>
    </div>
  );
}
