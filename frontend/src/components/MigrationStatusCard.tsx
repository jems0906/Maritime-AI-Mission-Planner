import { MigrationStatus } from "../types/mission";

type MigrationStatusCardProps = {
  status: MigrationStatus | null;
  error: string;
  loading: boolean;
  onRefresh: () => void;
};

export function MigrationStatusCard({ status, error, loading, onRefresh }: MigrationStatusCardProps) {
  return (
    <div className="card">
      <div className="button-row report-header-row">
        <h3>Migration Status</h3>
        <button onClick={onRefresh} disabled={loading}>
          {loading ? "Checking..." : "Refresh"}
        </button>
      </div>
      <p className="muted">Admin view for database revision drift between current schema and migration head.</p>

      {error && <div className="toast error">{error}</div>}

      {!error && !status && <div className="muted">Status unavailable. Configure admin key and refresh.</div>}

      {status && (
        <div className="migration-grid">
          <div>
            <strong>Current Revision</strong>
            <div>{status.current_revision ?? "none"}</div>
          </div>
          <div>
            <strong>Head Revision</strong>
            <div>{status.head_revision ?? "none"}</div>
          </div>
          <div>
            <strong>Up To Date</strong>
            <div>
              <span className={`status ${status.is_up_to_date ? "accept" : "reject"}`}>
                {status.is_up_to_date ? "yes" : "no"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
