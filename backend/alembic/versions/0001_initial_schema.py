"""Initial maritime mission planner schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("grid_rows", sa.Integer(), nullable=False),
        sa.Column("grid_cols", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scenarios_id"), "scenarios", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_normalized_name"), "users", ["normalized_name"], unique=False)

    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("sector_code", sa.String(length=16), nullable=False),
        sa.Column("row_idx", sa.Integer(), nullable=False),
        sa.Column("col_idx", sa.Integer(), nullable=False),
        sa.Column("weather_score", sa.Float(), nullable=False),
        sa.Column("sea_state", sa.Float(), nullable=False),
        sa.Column("sensor_confidence", sa.Float(), nullable=False),
        sa.Column("elapsed_search_minutes", sa.Float(), nullable=False),
        sa.Column("reported_anomalies", sa.Integer(), nullable=False),
        sa.Column("coverage_ratio", sa.Float(), nullable=False),
        sa.Column("has_ground_truth_anomaly", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sectors_id"), "sectors", ["id"], unique=False)
    op.create_index(op.f("ix_sectors_scenario_id"), "sectors", ["scenario_id"], unique=False)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("sector_id", sa.Integer(), nullable=False),
        sa.Column("priority_rank", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("model_confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendations_id"), "recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_recommendations_scenario_id"), "recommendations", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_recommendations_sector_id"), "recommendations", ["sector_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=True),
        sa.Column("recommendation_id", sa.Integer(), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)

    op.create_table(
        "review_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recommendation_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_name", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("override_rank", sa.Integer(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id"),
    )
    op.create_index(op.f("ix_review_decisions_id"), "review_decisions", ["id"], unique=False)
    op.create_index(op.f("ix_review_decisions_reviewer_id"), "review_decisions", ["reviewer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_decisions_reviewer_id"), table_name="review_decisions")
    op.drop_index(op.f("ix_review_decisions_id"), table_name="review_decisions")
    op.drop_table("review_decisions")

    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_recommendations_sector_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_scenario_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_id"), table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index(op.f("ix_sectors_scenario_id"), table_name="sectors")
    op.drop_index(op.f("ix_sectors_id"), table_name="sectors")
    op.drop_table("sectors")

    op.drop_index(op.f("ix_users_normalized_name"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_scenarios_id"), table_name="scenarios")
    op.drop_table("scenarios")
