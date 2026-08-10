from __future__ import annotations

import random
from typing import Any


def _sector_code(row_idx: int, col_idx: int) -> str:
    # Grid names like A01, B03 keep map labels operator-friendly.
    return f"{chr(65 + row_idx)}{col_idx + 1:02d}"


def generate_synthetic_sectors(rows: int, cols: int, seed: int | None = None) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    sectors: list[dict[str, Any]] = []

    for row in range(rows):
        for col in range(cols):
            weather_score = round(rng.uniform(0.2, 0.95), 3)
            sea_state = round(rng.uniform(0.15, 0.95), 3)
            sensor_confidence = round(rng.uniform(0.25, 0.98), 3)
            elapsed_search_minutes = round(rng.uniform(10, 240), 1)
            coverage_ratio = round(rng.uniform(0.15, 0.98), 3)

            anomaly_signal = (
                0.35 * weather_score
                + 0.25 * sea_state
                + 0.2 * (1 - sensor_confidence)
                + 0.2 * (1 - coverage_ratio)
            )
            reported_anomalies = int(max(0, round((anomaly_signal + rng.uniform(-0.15, 0.25)) * 6)))
            has_ground_truth_anomaly = anomaly_signal + rng.uniform(-0.2, 0.2) > 0.62

            sectors.append(
                {
                    "sector_code": _sector_code(row, col),
                    "row_idx": row,
                    "col_idx": col,
                    "weather_score": weather_score,
                    "sea_state": sea_state,
                    "sensor_confidence": sensor_confidence,
                    "elapsed_search_minutes": elapsed_search_minutes,
                    "reported_anomalies": reported_anomalies,
                    "coverage_ratio": coverage_ratio,
                    "has_ground_truth_anomaly": has_ground_truth_anomaly,
                }
            )

    return sectors
