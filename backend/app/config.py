from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./maritime.db")
        self.model_path = os.getenv("MODEL_PATH", "ml_artifacts/ranker.joblib")
        self.operator_api_key = os.getenv("OPERATOR_API_KEY", "")
        self.reviewer_api_key = os.getenv("REVIEWER_API_KEY", "")
        self.admin_api_key = os.getenv("ADMIN_API_KEY", "")
        self.auto_create_schema = os.getenv("AUTO_CREATE_SCHEMA", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.cors_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    @property
    def model_path_abs(self) -> Path:
        return Path(self.model_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
