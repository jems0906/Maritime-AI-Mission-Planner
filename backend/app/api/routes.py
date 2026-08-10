from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import engine, get_db
from app.models.entities import AuditLog, Recommendation, ReviewDecision, Scenario, Sector, User
from app.api.security import require_admin, require_operator, require_reviewer
from app.schemas.dto import (
    AuditLogOut,
    MigrationStatusOut,
    RankResponse,
    RecommendationOut,
    ReportOut,
    ReviewOut,
    ReviewRequest,
    ScenarioDetailOut,
    ScenarioGenerateRequest,
    ScenarioOut,
    ScenarioUploadRequest,
    SectorOut,
    TrainRequest,
    TrainResponse,
    UserOut,
)
from app.services.audit import write_audit
from app.services.csv_upload import parse_sector_csv
from app.services.ml_ranker import RankerService
from app.services.migration_status import get_migration_status
from app.services.reporting import build_after_action_report, render_report_markdown
from app.services.synthetic_data import generate_synthetic_sectors

router = APIRouter(prefix="/api", tags=["maritime-mission"])
ranker = RankerService()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/system/migration-status", response_model=MigrationStatusOut)
def migration_status(_: None = Depends(require_admin)) -> MigrationStatusOut:
    status = get_migration_status(engine)
    return MigrationStatusOut.model_validate(status)


@router.post("/scenarios/generate", response_model=ScenarioOut)
def generate_scenario(
    payload: ScenarioGenerateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_operator),
) -> ScenarioOut:
    scenario = Scenario(name=payload.name, grid_rows=payload.rows, grid_cols=payload.cols)
    db.add(scenario)
    db.flush()

    generated = generate_synthetic_sectors(payload.rows, payload.cols, payload.seed)
    sectors = [Sector(scenario_id=scenario.id, **item) for item in generated]
    db.add_all(sectors)

    write_audit(
        db,
        actor="system",
        action_type="scenario_generated",
        scenario_id=scenario.id,
        details={"rows": payload.rows, "cols": payload.cols, "seed": payload.seed},
    )

    db.commit()
    db.refresh(scenario)
    return ScenarioOut.model_validate(scenario)


@router.post("/scenarios/upload", response_model=ScenarioOut)
def upload_scenario(
    payload: ScenarioUploadRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_operator),
) -> ScenarioOut:
    expected = payload.rows * payload.cols
    if len(payload.sectors) != expected:
        raise HTTPException(status_code=400, detail=f"Expected {expected} sectors but received {len(payload.sectors)}")

    scenario = Scenario(name=payload.name, grid_rows=payload.rows, grid_cols=payload.cols)
    db.add(scenario)
    db.flush()

    sectors = [Sector(scenario_id=scenario.id, **sector.model_dump()) for sector in payload.sectors]
    db.add_all(sectors)

    write_audit(
        db,
        actor="operator",
        action_type="scenario_uploaded",
        scenario_id=scenario.id,
        details={"sector_count": len(payload.sectors)},
    )

    db.commit()
    db.refresh(scenario)
    return ScenarioOut.model_validate(scenario)


@router.post("/scenarios/upload-csv", response_model=ScenarioOut)
async def upload_scenario_csv(
    name: str = Form(...),
    rows: int = Form(...),
    cols: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_operator),
) -> ScenarioOut:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    content = await file.read()
    try:
        sectors_parsed = parse_sector_csv(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    expected = rows * cols
    if len(sectors_parsed) != expected:
        raise HTTPException(
            status_code=400,
            detail=f"CSV row count mismatch: expected {expected} sectors but received {len(sectors_parsed)}",
        )

    scenario = Scenario(name=name, grid_rows=rows, grid_cols=cols)
    db.add(scenario)
    db.flush()

    sectors = [Sector(scenario_id=scenario.id, **sector) for sector in sectors_parsed]
    db.add_all(sectors)

    write_audit(
        db,
        actor="operator",
        action_type="scenario_uploaded_csv",
        scenario_id=scenario.id,
        details={"sector_count": len(sectors_parsed), "filename": file.filename},
    )

    db.commit()
    db.refresh(scenario)
    return ScenarioOut.model_validate(scenario)


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[UserOut]:
    users = db.execute(select(User).order_by(User.display_name.asc())).scalars().all()
    return [UserOut.model_validate(user) for user in users]


@router.get("/scenarios", response_model=list[ScenarioOut])
def list_scenarios(db: Session = Depends(get_db)) -> list[ScenarioOut]:
    scenarios = db.execute(select(Scenario).order_by(Scenario.created_at.desc())).scalars().all()
    return [ScenarioOut.model_validate(item) for item in scenarios]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailOut)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)) -> ScenarioDetailOut:
    scenario = db.execute(
        select(Scenario).options(selectinload(Scenario.sectors)).where(Scenario.id == scenario_id)
    ).scalar_one_or_none()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return ScenarioDetailOut(
        scenario=ScenarioOut.model_validate(scenario),
        sectors=[SectorOut.model_validate(sector) for sector in scenario.sectors],
    )


@router.post("/scenarios/{scenario_id}/rank", response_model=RankResponse)
def rank_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_operator),
) -> RankResponse:
    scenario = db.execute(
        select(Scenario)
        .options(selectinload(Scenario.sectors), selectinload(Scenario.recommendations))
        .where(Scenario.id == scenario_id)
    ).scalar_one_or_none()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    recommendations, model_used = ranker.rank_scenario(db, scenario)
    write_audit(
        db,
        actor="system",
        action_type="ranking_generated",
        scenario_id=scenario.id,
        details={"recommendation_count": len(recommendations), "model": model_used},
    )
    db.commit()

    output = [RecommendationOut.model_validate(rec) for rec in recommendations]
    return RankResponse(scenario_id=scenario.id, recommendations=output, model_used=model_used)


@router.get("/scenarios/{scenario_id}/recommendations", response_model=list[RecommendationOut])
def list_recommendations(scenario_id: int, db: Session = Depends(get_db)) -> list[RecommendationOut]:
    recs = db.execute(
        select(Recommendation)
        .where(Recommendation.scenario_id == scenario_id)
        .order_by(Recommendation.priority_rank.asc())
    ).scalars().all()
    return [RecommendationOut.model_validate(item) for item in recs]


@router.post("/recommendations/{recommendation_id}/review", response_model=ReviewOut)
def review_recommendation(
    recommendation_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_reviewer),
) -> ReviewOut:
    recommendation = db.execute(
        select(Recommendation)
        .options(selectinload(Recommendation.review_decision))
        .where(Recommendation.id == recommendation_id)
    ).scalar_one_or_none()

    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if recommendation.review_decision is not None:
        raise HTTPException(status_code=409, detail="Recommendation already reviewed")

    normalized_name = payload.reviewer_name.strip().lower()
    reviewer = db.execute(select(User).where(User.normalized_name == normalized_name)).scalar_one_or_none()
    if reviewer is None:
        reviewer = User(display_name=payload.reviewer_name.strip(), normalized_name=normalized_name)
        db.add(reviewer)
        db.flush()

    decision = ReviewDecision(
        recommendation_id=recommendation.id,
        reviewer_id=reviewer.id,
        reviewer_name=payload.reviewer_name,
        action=payload.action,
        override_rank=payload.override_rank,
        justification=payload.justification,
    )
    db.add(decision)

    recommendation.status = payload.action
    if payload.action == "override" and payload.override_rank is not None:
        recommendation.priority_rank = payload.override_rank

    write_audit(
        db,
        actor=payload.reviewer_name,
        action_type="recommendation_reviewed",
        scenario_id=recommendation.scenario_id,
        recommendation_id=recommendation.id,
        details={
            "action": payload.action,
            "override_rank": payload.override_rank,
            "justification": payload.justification,
        },
    )

    db.commit()
    db.refresh(decision)
    return ReviewOut.model_validate(decision)


@router.post("/admin/train", response_model=TrainResponse)
def train_model(
    payload: TrainRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> TrainResponse:
    try:
        sample_count = ranker.train(db, payload.scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    write_audit(
        db,
        actor="admin",
        action_type="model_trained",
        scenario_id=payload.scenario_id,
        details={"samples": sample_count},
    )
    db.commit()
    return TrainResponse(message="Model trained successfully", samples=sample_count)


@router.get("/scenarios/{scenario_id}/report", response_model=ReportOut)
def get_report(scenario_id: int, db: Session = Depends(get_db)) -> ReportOut:
    scenario = db.execute(
        select(Scenario)
        .options(
            selectinload(Scenario.sectors),
            selectinload(Scenario.recommendations)
            .selectinload(Recommendation.sector),
            selectinload(Scenario.recommendations)
            .selectinload(Recommendation.review_decision),
        )
        .where(Scenario.id == scenario_id)
    ).scalar_one_or_none()

    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return build_after_action_report(scenario)


@router.get("/scenarios/{scenario_id}/report.md", response_class=PlainTextResponse)
def get_report_markdown(scenario_id: int, db: Session = Depends(get_db)) -> str:
    scenario = db.execute(
        select(Scenario)
        .options(
            selectinload(Scenario.sectors),
            selectinload(Scenario.recommendations).selectinload(Recommendation.sector),
            selectinload(Scenario.recommendations).selectinload(Recommendation.review_decision),
        )
        .where(Scenario.id == scenario_id)
    ).scalar_one_or_none()

    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    report = build_after_action_report(scenario)
    return render_report_markdown(report)


@router.get("/scenarios/{scenario_id}/audit", response_model=list[AuditLogOut])
def get_audit_history(scenario_id: int, db: Session = Depends(get_db)) -> list[AuditLogOut]:
    logs = db.execute(
        select(AuditLog)
        .where(AuditLog.scenario_id == scenario_id)
        .order_by(AuditLog.created_at.desc())
    ).scalars().all()
    return [AuditLogOut.model_validate(item) for item in logs]
