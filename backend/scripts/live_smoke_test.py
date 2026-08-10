from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def _request_json(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> tuple[int, dict | list | str]:
    body = None
    merged_headers = {"Accept": "application/json"}
    if headers:
        merged_headers.update(headers)

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        merged_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, method=method, data=body, headers=merged_headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.getcode()
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to call {url}: {exc}") from exc

    if not raw:
        return status, {}

    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def _require_status(status: int, expected: int, step: str, data: object) -> None:
    if status != expected:
        raise RuntimeError(f"{step} failed: expected {expected}, got {status}, response={data}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live smoke checks against deployed API")
    parser.add_argument("--base-url", required=True, help="API base URL, example: https://svc.up.railway.app/api")
    parser.add_argument("--operator-key", default="", help="Value for X-Operator-Key")
    parser.add_argument("--reviewer-key", default="", help="Value for X-Reviewer-Key")
    parser.add_argument("--admin-key", default="", help="Value for X-Admin-Key")
    parser.add_argument(
        "--strict-keys",
        action="store_true",
        help="Fail if role keys are not provided for protected-route smoke checks",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    health_status, health = _request_json("GET", f"{base_url}/health")
    _require_status(health_status, 200, "health", health)

    results: dict[str, object] = {
        "health": health_status,
        "protected_flow_executed": False,
    }

    has_keys = bool(args.operator_key and args.reviewer_key and args.admin_key)
    if args.strict_keys and not has_keys:
        raise RuntimeError("strict-keys enabled but one or more role keys are missing")

    if not has_keys:
        scenarios_status, scenarios = _request_json("GET", f"{base_url}/scenarios")
        _require_status(scenarios_status, 200, "list_scenarios", scenarios)
        results["scenarios"] = scenarios_status
        print("LIVE_SMOKE_OK", json.dumps(results))
        return

    operator_headers = {"X-Operator-Key": args.operator_key}
    reviewer_headers = {"X-Reviewer-Key": args.reviewer_key}
    admin_headers = {"X-Admin-Key": args.admin_key}

    migration_status, migration = _request_json("GET", f"{base_url}/system/migration-status", headers=admin_headers)
    _require_status(migration_status, 200, "migration_status", migration)

    generated_status, generated = _request_json(
        "POST",
        f"{base_url}/scenarios/generate",
        headers=operator_headers,
        payload={"name": "Live Smoke Mission", "rows": 4, "cols": 4, "seed": 9},
    )
    _require_status(generated_status, 200, "generate", generated)
    scenario_id = generated["id"]

    ranked_status, ranked = _request_json(
        "POST",
        f"{base_url}/scenarios/{scenario_id}/rank",
        headers=operator_headers,
    )
    _require_status(ranked_status, 200, "rank", ranked)
    recommendation_id = ranked["recommendations"][0]["id"]

    reviewed_status, reviewed = _request_json(
        "POST",
        f"{base_url}/recommendations/{recommendation_id}/review",
        headers=reviewer_headers,
        payload={
            "reviewer_name": "Live Smoke Reviewer",
            "action": "accept",
            "justification": "Live smoke validation of review flow",
        },
    )
    _require_status(reviewed_status, 200, "review", reviewed)

    report_status, report = _request_json("GET", f"{base_url}/scenarios/{scenario_id}/report")
    _require_status(report_status, 200, "report", report)

    audit_status, audit = _request_json("GET", f"{base_url}/scenarios/{scenario_id}/audit")
    _require_status(audit_status, 200, "audit", audit)

    results.update(
        {
            "protected_flow_executed": True,
            "migration_status": migration_status,
            "generate": generated_status,
            "rank": ranked_status,
            "review": reviewed_status,
            "report": report_status,
            "audit": audit_status,
            "audit_count": len(audit) if isinstance(audit, list) else None,
            "scenario_id": scenario_id,
        }
    )
    print("LIVE_SMOKE_OK", json.dumps(results))


if __name__ == "__main__":
    main()
