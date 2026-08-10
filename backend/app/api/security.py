from __future__ import annotations

import os

from fastapi import Header, HTTPException

def _assert_key(configured_key: str, provided_key: str | None, role_name: str) -> None:
    if not configured_key:
        return
    if provided_key != configured_key:
        raise HTTPException(status_code=403, detail=f"Invalid {role_name} key")


def require_operator(x_operator_key: str | None = Header(default=None, alias="X-Operator-Key")) -> None:
    _assert_key(os.getenv("OPERATOR_API_KEY", ""), x_operator_key, "operator")


def require_reviewer(x_reviewer_key: str | None = Header(default=None, alias="X-Reviewer-Key")) -> None:
    _assert_key(os.getenv("REVIEWER_API_KEY", ""), x_reviewer_key, "reviewer")


def require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    _assert_key(os.getenv("ADMIN_API_KEY", ""), x_admin_key, "admin")
