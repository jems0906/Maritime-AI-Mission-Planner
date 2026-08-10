from __future__ import annotations

from app.models.entities import Recommendation, Scenario
from app.schemas.dto import ReportOut


def build_after_action_report(scenario: Scenario) -> ReportOut:
    sectors = list(scenario.sectors)
    recommendations = sorted(list(scenario.recommendations), key=lambda row: row.priority_rank)

    coverage = 0.0
    if sectors:
        coverage = sum(sector.coverage_ratio for sector in sectors) / len(sectors)

    reviewed = [rec for rec in recommendations if rec.review_decision is not None]
    accepted = [rec for rec in reviewed if rec.review_decision and rec.review_decision.action == "accept"]
    rejected = [rec for rec in reviewed if rec.review_decision and rec.review_decision.action == "reject"]
    overridden = [rec for rec in reviewed if rec.review_decision and rec.review_decision.action == "override"]

    model_precision = 0.0
    model_recall = 0.0
    if recommendations:
        top_k = max(1, len(recommendations) // 4)
        top_recs = recommendations[:top_k]

        true_positive_ids = {
            rec.id
            for rec in top_recs
            if rec.sector.has_ground_truth_anomaly or rec.sector.coverage_ratio < 0.65
        }
        all_true_ids = {
            rec.id
            for rec in recommendations
            if rec.sector.has_ground_truth_anomaly or rec.sector.coverage_ratio < 0.65
        }

        model_precision = len(true_positive_ids) / len(top_recs) if top_recs else 0.0
        model_recall = len(true_positive_ids) / len(all_true_ids) if all_true_ids else 0.0

    override_rate = len(overridden) / len(reviewed) if reviewed else 0.0

    improvements: list[str] = []
    if model_precision < 0.6:
        improvements.append("Collect additional labeled synthetic scenarios to improve anomaly precision.")
    if override_rate > 0.25:
        improvements.append("Review feature weighting and threshold calibration due to high operator override rate.")
    if coverage < 0.75:
        improvements.append("Prioritize sectors with low coverage in subsequent sorties before expanding search perimeter.")
    if not improvements:
        improvements.append("Maintain current model and continue periodic retraining with newly reviewed missions.")

    return ReportOut(
        scenario_id=scenario.id,
        mission_coverage_percent=round(coverage * 100, 2),
        reviewed_count=len(reviewed),
        pending_count=len(recommendations) - len(reviewed),
        accepted_count=len(accepted),
        rejected_count=len(rejected),
        overridden_count=len(overridden),
        model_precision_at_25=round(model_precision, 3),
        model_recall_at_25=round(model_recall, 3),
        human_override_rate=round(override_rate, 3),
        improvement_recommendations=improvements,
    )


def render_report_markdown(report: ReportOut) -> str:
    lines: list[str] = []
    lines.append(f"# After-Action Report: Scenario {report.scenario_id}")
    lines.append("")
    lines.append("## Governance Notice")
    lines.append(
        "This report summarizes recommendation outputs and human review actions. Final tasking decisions remain human-authorized."
    )
    lines.append("")
    lines.append("## Mission Metrics")
    lines.append(f"- Mission coverage: {report.mission_coverage_percent:.1f}%")
    lines.append(f"- Reviewed recommendations: {report.reviewed_count}")
    lines.append(f"- Pending recommendations: {report.pending_count}")
    lines.append(f"- Accepted: {report.accepted_count}")
    lines.append(f"- Rejected: {report.rejected_count}")
    lines.append(f"- Overridden: {report.overridden_count}")
    lines.append("")
    lines.append("## Model Performance")
    lines.append(f"- Precision@25%: {report.model_precision_at_25 * 100:.1f}%")
    lines.append(f"- Recall@25%: {report.model_recall_at_25 * 100:.1f}%")
    lines.append(f"- Human override rate: {report.human_override_rate * 100:.1f}%")
    lines.append("")
    lines.append("## Improvement Recommendations")
    for item in report.improvement_recommendations:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
