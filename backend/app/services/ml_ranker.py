from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import Recommendation, Scenario, Sector

FEATURE_NAMES = [
    "weather_score",
    "sea_state",
    "sensor_confidence",
    "elapsed_search_minutes",
    "reported_anomalies",
    "coverage_ratio",
]


class RankerService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _model_path(self) -> Path:
        path = self.settings.model_path_abs
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def train(self, db: Session, scenario_id: int | None = None) -> int:
        sectors_stmt = select(Sector)
        if scenario_id is not None:
            sectors_stmt = sectors_stmt.where(Sector.scenario_id == scenario_id)

        sectors = db.execute(sectors_stmt).scalars().all()
        if len(sectors) < 20:
            raise ValueError("Need at least 20 sector samples to train model")

        x = np.array([self._features_for_sector(s) for s in sectors], dtype=float)
        y = np.array([self._label_for_sector(s) for s in sectors], dtype=int)

        pipeline = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=500)),
            ]
        )
        pipeline.fit(x, y)
        joblib.dump(pipeline, self._model_path())
        return len(sectors)

    def rank_scenario(self, db: Session, scenario: Scenario) -> tuple[list[Recommendation], str]:
        sectors = list(scenario.sectors)
        if not sectors:
            return [], "none"

        model = self._load_model()
        model_used = "logistic_regression" if model is not None else "heuristic_fallback"

        for rec in list(scenario.recommendations):
            db.delete(rec)
        db.flush()

        scored_rows: list[dict[str, Any]] = []
        for sector in sectors:
            if model is None:
                risk_score, confidence, explanation = self._heuristic_score(sector)
            else:
                risk_score, confidence, explanation = self._model_score(model, sector)

            scored_rows.append(
                {
                    "sector": sector,
                    "risk_score": float(risk_score),
                    "confidence": float(confidence),
                    "explanation": explanation,
                }
            )

        scored_rows.sort(key=lambda row: row["risk_score"], reverse=True)

        recommendations: list[Recommendation] = []
        for idx, row in enumerate(scored_rows, start=1):
            recommendation = Recommendation(
                scenario_id=scenario.id,
                sector_id=row["sector"].id,
                priority_rank=idx,
                risk_score=row["risk_score"],
                model_confidence=row["confidence"],
                explanation=row["explanation"],
                status="pending",
            )
            db.add(recommendation)
            recommendations.append(recommendation)

        db.flush()
        return recommendations, model_used

    def _load_model(self) -> Pipeline | None:
        model_path = self._model_path()
        if not model_path.exists():
            return None
        try:
            model = joblib.load(model_path)
            if isinstance(model, Pipeline):
                return model
        except Exception:
            return None
        return None

    def _features_for_sector(self, sector: Sector) -> list[float]:
        return [
            float(sector.weather_score),
            float(sector.sea_state),
            float(sector.sensor_confidence),
            float(sector.elapsed_search_minutes),
            float(sector.reported_anomalies),
            float(sector.coverage_ratio),
        ]

    def _label_for_sector(self, sector: Sector) -> int:
        return int(sector.has_ground_truth_anomaly or sector.coverage_ratio < 0.65)

    def _heuristic_score(self, sector: Sector) -> tuple[float, float, dict[str, Any]]:
        weights = {
            "weather_score": 0.2,
            "sea_state": 0.2,
            "sensor_confidence": -0.2,
            "elapsed_search_minutes": 0.1,
            "reported_anomalies": 0.2,
            "coverage_ratio": -0.3,
        }
        f = self._features_for_sector(sector)
        normalized_elapsed = min(f[3] / 240.0, 1.0)
        normalized_anomalies = min(f[4] / 8.0, 1.0)

        transformed = [
            f[0],
            f[1],
            f[2],
            normalized_elapsed,
            normalized_anomalies,
            f[5],
        ]

        weighted_sum = (
            weights["weather_score"] * transformed[0]
            + weights["sea_state"] * transformed[1]
            + weights["sensor_confidence"] * transformed[2]
            + weights["elapsed_search_minutes"] * transformed[3]
            + weights["reported_anomalies"] * transformed[4]
            + weights["coverage_ratio"] * transformed[5]
        )

        risk_score = float(np.clip(0.5 + weighted_sum, 0.0, 1.0))
        confidence = float(np.clip(0.55 + abs(risk_score - 0.5), 0.0, 1.0))

        explanation = {
            "top_factors": self._top_factors_from_weights(weights, transformed),
            "coverage_status": "incomplete" if sector.coverage_ratio < 0.75 else "adequate",
            "method": "heuristic",
        }
        return risk_score, confidence, explanation

    def _model_score(self, model: Pipeline, sector: Sector) -> tuple[float, float, dict[str, Any]]:
        x_raw = np.array([self._features_for_sector(sector)], dtype=float)
        probability = float(model.predict_proba(x_raw)[0][1])
        confidence = float(max(probability, 1 - probability))

        scaler: StandardScaler = model.named_steps["scaler"]
        clf: LogisticRegression = model.named_steps["clf"]
        x_std = scaler.transform(x_raw)[0]
        contribution_scores = x_std * clf.coef_[0]

        factors = [
            {
                "feature": name,
                "contribution": round(float(score), 4),
                "direction": "increases" if score >= 0 else "decreases",
            }
            for name, score in zip(FEATURE_NAMES, contribution_scores, strict=True)
        ]
        factors.sort(key=lambda factor: abs(factor["contribution"]), reverse=True)

        explanation = {
            "top_factors": factors[:3],
            "coverage_status": "incomplete" if sector.coverage_ratio < 0.75 else "adequate",
            "method": "logistic_regression",
        }
        return probability, confidence, explanation

    def _top_factors_from_weights(self, weights: dict[str, float], transformed: list[float]) -> list[dict[str, Any]]:
        contributions = [
            ("weather_score", transformed[0] * weights["weather_score"]),
            ("sea_state", transformed[1] * weights["sea_state"]),
            ("sensor_confidence", transformed[2] * weights["sensor_confidence"]),
            ("elapsed_search_minutes", transformed[3] * weights["elapsed_search_minutes"]),
            ("reported_anomalies", transformed[4] * weights["reported_anomalies"]),
            ("coverage_ratio", transformed[5] * weights["coverage_ratio"]),
        ]
        contributions.sort(key=lambda entry: abs(entry[1]), reverse=True)
        return [
            {
                "feature": feature,
                "contribution": round(float(value), 4),
                "direction": "increases" if value >= 0 else "decreases",
            }
            for feature, value in contributions[:3]
        ]
