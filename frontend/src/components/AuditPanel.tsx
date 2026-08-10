import { AuditLog } from "../types/mission";

type AuditPanelProps = {
  logs: AuditLog[];
};

export function AuditPanel({ logs }: AuditPanelProps) {
  return (
    <div className="card">
      <h3>Audit History</h3>
      <p className="muted">Every recommendation decision and model action is logged for traceability.</p>
      {!logs.length && <div className="muted">No audit entries yet for this scenario.</div>}
      {!!logs.length && (
        <div className="audit-list">
          {logs.map((entry) => (
            <div key={entry.id} className="audit-item">
              <div>
                <strong>{entry.action_type}</strong> by {entry.actor}
              </div>
              <div className="muted">{new Date(entry.created_at).toLocaleString()}</div>
              <pre>{JSON.stringify(entry.details, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
