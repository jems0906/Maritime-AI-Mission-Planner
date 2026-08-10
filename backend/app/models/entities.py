from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    review_decisions: Mapped[list[ReviewDecision]] = relationship("ReviewDecision", back_populates="reviewer")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_cols: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    sectors: Mapped[list[Sector]] = relationship("Sector", back_populates="scenario", cascade="all, delete-orphan")
    recommendations: Mapped[list[Recommendation]] = relationship(
        "Recommendation", back_populates="scenario", cascade="all, delete-orphan"
    )


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    sector_code: Mapped[str] = mapped_column(String(16), nullable=False)
    row_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    col_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    weather_score: Mapped[float] = mapped_column(Float, nullable=False)
    sea_state: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    elapsed_search_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    reported_anomalies: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    has_ground_truth_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    scenario: Mapped[Scenario] = relationship("Scenario", back_populates="sectors")
    recommendation: Mapped[Recommendation] = relationship(
        "Recommendation", back_populates="sector", uselist=False
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id", ondelete="CASCADE"), nullable=False, index=True)
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    model_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    scenario: Mapped[Scenario] = relationship("Scenario", back_populates="recommendations")
    sector: Mapped[Sector] = relationship("Sector", back_populates="recommendation")
    review_decision: Mapped[ReviewDecision] = relationship(
        "ReviewDecision", back_populates="recommendation", uselist=False, cascade="all, delete-orphan"
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    override_rank: Mapped[int] = mapped_column(Integer, nullable=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    recommendation: Mapped[Recommendation] = relationship("Recommendation", back_populates="review_decision")
    reviewer: Mapped[User] = relationship("User", back_populates="review_decisions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
