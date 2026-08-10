from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import AuditLog


def write_audit(
    db: Session,
    *,
    actor: str,
    action_type: str,
    details: dict,
    scenario_id: int | None = None,
    recommendation_id: int | None = None,
) -> AuditLog:
    log = AuditLog(
        actor=actor,
        action_type=action_type,
        details=details,
        scenario_id=scenario_id,
        recommendation_id=recommendation_id,
    )
    db.add(log)
    return log
