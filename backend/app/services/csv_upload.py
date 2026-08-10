from __future__ import annotations

import csv
import io
from typing import Any

from app.schemas.dto import SectorCreate


def parse_sector_csv(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    sectors: list[dict[str, Any]] = []

    for idx, row in enumerate(reader, start=2):
        try:
            sector = SectorCreate(
                sector_code=row["sector_code"],
                row_idx=int(row["row_idx"]),
                col_idx=int(row["col_idx"]),
                weather_score=float(row["weather_score"]),
                sea_state=float(row["sea_state"]),
                sensor_confidence=float(row["sensor_confidence"]),
                elapsed_search_minutes=float(row["elapsed_search_minutes"]),
                reported_anomalies=int(row["reported_anomalies"]),
                coverage_ratio=float(row["coverage_ratio"]),
                has_ground_truth_anomaly=str(row.get("has_ground_truth_anomaly", "false")).lower()
                in {"1", "true", "yes"},
            )
        except Exception as exc:
            raise ValueError(f"Invalid CSV row at line {idx}: {exc}") from exc
        sectors.append(sector.model_dump())

    return sectors
