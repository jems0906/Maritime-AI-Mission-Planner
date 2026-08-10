from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SectorCreate(BaseModel):
    sector_code: str
    row_idx: int
    col_idx: int
    weather_score: float = Field(ge=0.0, le=1.0)
    sea_state: float = Field(ge=0.0, le=1.0)
    sensor_confidence: float = Field(ge=0.0, le=1.0)
    elapsed_search_minutes: float = Field(ge=0.0)
    reported_anomalies: int = Field(ge=0)
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    has_ground_truth_anomaly: bool = False


class ScenarioGenerateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    rows: int = Field(ge=2, le=50)
    cols: int = Field(ge=2, le=50)
    seed: int | None = None


class ScenarioUploadRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    rows: int = Field(ge=2, le=50)
    cols: int = Field(ge=2, le=50)
    sectors: list[SectorCreate]


class ScenarioOut(BaseModel):
    id: int
    name: str
    grid_rows: int
    grid_cols: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    display_name: str
    normalized_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SectorOut(BaseModel):
    id: int
    scenario_id: int
    sector_code: str
    row_idx: int
    col_idx: int
    weather_score: float
    sea_state: float
    sensor_confidence: float
    elapsed_search_minutes: float
    reported_anomalies: int
    coverage_ratio: float
    has_ground_truth_anomaly: bool

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    id: int
    scenario_id: int
    sector_id: int
    priority_rank: int
    risk_score: float
    model_confidence: float
    explanation: dict
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    reviewer_name: str = Field(min_length=2, max_length=255)
    action: Literal["accept", "reject", "override"]
    override_rank: int | None = Field(default=None, ge=1)
    justification: str = Field(min_length=5)

    @model_validator(mode="after")
    def validate_override(self) -> "ReviewRequest":
        if self.action == "override" and self.override_rank is None:
            raise ValueError("override_rank is required when action is override")
        return self


class ReviewOut(BaseModel):
    id: int
    recommendation_id: int
    reviewer_id: int
    reviewer_name: str
    action: str
    override_rank: int | None
    justification: str
    decided_at: datetime

    model_config = {"from_attributes": True}


class ScenarioDetailOut(BaseModel):
    scenario: ScenarioOut
    sectors: list[SectorOut]


class RankResponse(BaseModel):
    scenario_id: int
    recommendations: list[RecommendationOut]
    model_used: str


class TrainRequest(BaseModel):
    scenario_id: int | None = None


class TrainResponse(BaseModel):
    message: str
    samples: int


class ReportOut(BaseModel):
    scenario_id: int
    mission_coverage_percent: float
    reviewed_count: int
    pending_count: int
    accepted_count: int
    rejected_count: int
    overridden_count: int
    model_precision_at_25: float
    model_recall_at_25: float
    human_override_rate: float
    improvement_recommendations: list[str]


class AuditLogOut(BaseModel):
    id: int
    scenario_id: int | None
    recommendation_id: int | None
    actor: str
    action_type: str
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class MigrationStatusOut(BaseModel):
    current_revision: str | None
    head_revision: str | None
    is_up_to_date: bool
