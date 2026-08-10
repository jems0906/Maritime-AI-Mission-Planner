import { Recommendation, Sector } from "../types/mission";

type ReviewDraft = {
  action: "accept" | "reject" | "override";
  overrideRank?: number;
  justification: string;
};

type RecommendationTableProps = {
  recommendations: Recommendation[];
  sectorsById: Map<number, Sector>;
  reviewerName: string;
  draftByRecommendation: Record<number, ReviewDraft>;
  onDraftChange: (recommendationId: number, next: ReviewDraft) => void;
  onSubmitReview: (recommendationId: number) => void;
  selectedSectorId: number | null;
  onSelectSector: (sectorId: number) => void;
};

export function RecommendationTable({
  recommendations,
  sectorsById,
  reviewerName,
  draftByRecommendation,
  onDraftChange,
  onSubmitReview,
  selectedSectorId,
  onSelectSector
}: RecommendationTableProps) {
  if (!recommendations.length) {
    return <div className="card">No recommendations yet. Rank the scenario to generate priorities.</div>;
  }

  return (
    <div className="card table-wrap">
      <h3>AI Recommendations</h3>
      <p className="muted">Every recommendation requires a human review decision and written justification.</p>
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Sector</th>
            <th>Risk</th>
            <th>Confidence</th>
            <th>Coverage</th>
            <th>Status</th>
            <th>Top Factors</th>
            <th>Human Review</th>
          </tr>
        </thead>
        <tbody>
          {recommendations.map((rec) => {
            const sector = sectorsById.get(rec.sector_id);
            const draft =
              draftByRecommendation[rec.id] ??
              ({ action: "accept", justification: "" } as ReviewDraft);
            const isSelected = selectedSectorId === rec.sector_id;

            return (
              <tr key={rec.id} className={isSelected ? "row-selected" : ""}>
                <td>{rec.priority_rank}</td>
                <td>
                  <button className="link-btn" onClick={() => onSelectSector(rec.sector_id)}>
                    {sector?.sector_code ?? rec.sector_id}
                  </button>
                </td>
                <td>{(rec.risk_score * 100).toFixed(1)}%</td>
                <td>{(rec.model_confidence * 100).toFixed(1)}%</td>
                <td>{sector ? `${(sector.coverage_ratio * 100).toFixed(0)}%` : "-"}</td>
                <td>
                  <span className={`status ${rec.status}`}>{rec.status}</span>
                </td>
                <td>
                  {rec.explanation.top_factors.map((factor) => (
                    <div key={`${rec.id}-${factor.feature}`} className="factor-line">
                      {factor.feature}: {factor.direction} ({factor.contribution.toFixed(2)})
                    </div>
                  ))}
                </td>
                <td>
                  {rec.status !== "pending" ? (
                    <div className="muted">Reviewed</div>
                  ) : (
                    <div className="review-form">
                      <select
                        value={draft.action}
                        onChange={(event) =>
                          onDraftChange(rec.id, {
                            ...draft,
                            action: event.target.value as "accept" | "reject" | "override"
                          })
                        }
                      >
                        <option value="accept">accept</option>
                        <option value="reject">reject</option>
                        <option value="override">override</option>
                      </select>

                      {draft.action === "override" && (
                        <input
                          type="number"
                          min={1}
                          placeholder="override rank"
                          value={draft.overrideRank ?? ""}
                          onChange={(event) =>
                            onDraftChange(rec.id, {
                              ...draft,
                              overrideRank: Number(event.target.value)
                            })
                          }
                        />
                      )}

                      <textarea
                        placeholder="Justification for this decision"
                        value={draft.justification}
                        onChange={(event) =>
                          onDraftChange(rec.id, { ...draft, justification: event.target.value })
                        }
                      />

                      <button disabled={!reviewerName.trim()} onClick={() => onSubmitReview(rec.id)}>
                        Submit Review
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
