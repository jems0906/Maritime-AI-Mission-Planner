from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Keep tests isolated from local demo DB.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite:///./test_mission_planner.db"
os.environ["MODEL_PATH"] = "ml_artifacts/test_ranker.joblib"
os.environ["OPERATOR_API_KEY"] = "operator-test-key"
os.environ["REVIEWER_API_KEY"] = "reviewer-test-key"
os.environ["ADMIN_API_KEY"] = "admin-test-key"

from app.main import app  # noqa: E402
from app.db.session import engine  # noqa: E402


OPERATOR_HEADERS = {"X-Operator-Key": "operator-test-key"}
REVIEWER_HEADERS = {"X-Reviewer-Key": "reviewer-test-key"}
ADMIN_HEADERS = {"X-Admin-Key": "admin-test-key"}


@pytest.fixture(autouse=True)
def cleanup_test_files() -> None:
    yield
    # Release pooled SQLite handles before removing test artifacts on Windows.
    engine.dispose()
    db_file = Path("test_mission_planner.db")
    if db_file.exists():
        for _ in range(5):
            try:
                db_file.unlink()
                break
            except PermissionError:
                time.sleep(0.2)
    model_file = Path("ml_artifacts/test_ranker.joblib")
    if model_file.exists():
        model_file.unlink()


def _csv_bytes() -> bytes:
    rows = [
        "sector_code,row_idx,col_idx,weather_score,sea_state,sensor_confidence,elapsed_search_minutes,reported_anomalies,coverage_ratio,has_ground_truth_anomaly",
        "A01,0,0,0.52,0.41,0.78,55,1,0.62,false",
        "A02,0,1,0.83,0.74,0.42,125,4,0.37,true",
        "A03,0,2,0.66,0.58,0.69,80,2,0.51,false",
        "A04,0,3,0.48,0.28,0.86,42,0,0.82,false",
        "B01,1,0,0.61,0.47,0.55,96,2,0.44,false",
        "B02,1,1,0.72,0.69,0.49,110,3,0.33,true",
        "B03,1,2,0.35,0.21,0.88,27,0,0.93,false",
        "B04,1,3,0.81,0.76,0.38,141,4,0.29,true",
        "C01,2,0,0.54,0.49,0.67,66,1,0.57,false",
        "C02,2,1,0.75,0.63,0.47,132,3,0.40,true",
        "C03,2,2,0.39,0.26,0.84,34,0,0.88,false",
        "C04,2,3,0.69,0.59,0.53,104,2,0.46,false",
        "D01,3,0,0.58,0.44,0.71,73,1,0.69,false",
        "D02,3,1,0.84,0.79,0.36,148,5,0.25,true",
        "D03,3,2,0.42,0.32,0.82,39,0,0.91,false",
        "D04,3,3,0.64,0.57,0.59,97,2,0.52,false",
    ]
    return "\n".join(rows).encode("utf-8")


def test_full_json_workflow() -> None:
    with TestClient(app) as client:
        migration_status = client.get("/api/system/migration-status", headers=ADMIN_HEADERS)
        assert migration_status.status_code == 200
        assert "is_up_to_date" in migration_status.json()

        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        generated = client.post(
            "/api/scenarios/generate",
            json={"name": "Pytest Mission", "rows": 4, "cols": 4, "seed": 4},
            headers=OPERATOR_HEADERS,
        )
        assert generated.status_code == 200
        scenario_id = generated.json()["id"]

        ranked = client.post(f"/api/scenarios/{scenario_id}/rank", headers=OPERATOR_HEADERS)
        assert ranked.status_code == 200
        assert len(ranked.json()["recommendations"]) == 16
        recommendation_id = ranked.json()["recommendations"][0]["id"]

        reviewed = client.post(
            f"/api/recommendations/{recommendation_id}/review",
            json={
                "reviewer_name": "Ops Officer",
                "action": "accept",
                "justification": "High composite risk and low coverage",
            },
            headers=REVIEWER_HEADERS,
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["reviewer_id"] > 0

        report = client.get(f"/api/scenarios/{scenario_id}/report")
        assert report.status_code == 200
        assert "mission_coverage_percent" in report.json()

        report_md = client.get(f"/api/scenarios/{scenario_id}/report.md")
        assert report_md.status_code == 200
        assert "After-Action Report" in report_md.text

        audit = client.get(f"/api/scenarios/{scenario_id}/audit")
        assert audit.status_code == 200
        assert len(audit.json()) >= 3

        users = client.get("/api/users")
        assert users.status_code == 200
        assert any(user["display_name"] == "Ops Officer" for user in users.json())

        trained = client.post("/api/admin/train", json={"scenario_id": scenario_id}, headers=ADMIN_HEADERS)
        assert trained.status_code == 400


def test_role_key_enforcement() -> None:
    with TestClient(app) as client:
        migration_status_forbidden = client.get("/api/system/migration-status")
        assert migration_status_forbidden.status_code == 403

        generated_no_key = client.post(
            "/api/scenarios/generate",
            json={"name": "No Key Mission", "rows": 4, "cols": 4, "seed": 8},
        )
        assert generated_no_key.status_code == 403

        generated = client.post(
            "/api/scenarios/generate",
            json={"name": "Keyed Mission", "rows": 4, "cols": 4, "seed": 8},
            headers=OPERATOR_HEADERS,
        )
        assert generated.status_code == 200
        scenario_id = generated.json()["id"]

        ranked = client.post(f"/api/scenarios/{scenario_id}/rank", headers=OPERATOR_HEADERS)
        assert ranked.status_code == 200
        recommendation_id = ranked.json()["recommendations"][0]["id"]

        wrong_reviewer = client.post(
            f"/api/recommendations/{recommendation_id}/review",
            json={
                "reviewer_name": "Ops Officer",
                "action": "accept",
                "justification": "Testing key enforcement",
            },
            headers={"X-Reviewer-Key": "wrong-key"},
        )
        assert wrong_reviewer.status_code == 403

        bad_admin = client.post("/api/admin/train", json={"scenario_id": scenario_id})
        assert bad_admin.status_code == 403


def test_csv_upload_workflow() -> None:
    with TestClient(app) as client:
        uploaded = client.post(
            "/api/scenarios/upload-csv",
            data={"name": "CSV Test", "rows": "4", "cols": "4"},
            files={"file": ("mission_upload.csv", _csv_bytes(), "text/csv")},
            headers=OPERATOR_HEADERS,
        )
        assert uploaded.status_code == 200
        scenario_id = uploaded.json()["id"]

        detail = client.get(f"/api/scenarios/{scenario_id}")
        assert detail.status_code == 200
        assert len(detail.json()["sectors"]) == 16
