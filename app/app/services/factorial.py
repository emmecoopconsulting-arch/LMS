from datetime import datetime, UTC
import logging
import httpx
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import Employee
from app.services.settings_store import get_setting

logger = logging.getLogger(__name__)


def _resolve_config(db: Session) -> tuple[str, str, str]:
    settings = get_settings()
    base_url = get_setting(db, "factorial_base_url", settings.factorial_base_url).strip()
    token = get_setting(db, "factorial_api_token", settings.factorial_api_token).strip()
    company_id = get_setting(db, "factorial_company_id", settings.factorial_company_id).strip()
    return base_url, token, company_id


def _extract_employee(raw: dict) -> dict:
    first_name = raw.get("first_name") or raw.get("name") or ""
    last_name = raw.get("last_name") or raw.get("surname") or ""
    active = bool(raw.get("active")) and not bool(raw.get("terminated_on") or raw.get("is_terminating"))
    office = raw.get("location") or raw.get("location_id") or ""
    cost_center = raw.get("cost_center") or raw.get("department") or raw.get("legal_entity_id") or ""
    return {
        "factorial_employee_id": str(raw.get("id")),
        "first_name": first_name or "N/A",
        "last_name": last_name or "N/A",
        "email": raw.get("email"),
        "location": office if isinstance(office, str) else str(office or ""),
        "cost_center": cost_center if isinstance(cost_center, str) else str(cost_center or ""),
        "is_active": active,
    }


def sync_factorial_employees(db: Session) -> dict:
    base_url, token, company_id = _resolve_config(db)
    if not base_url or not token:
        return {"ok": False, "message": "Factorial config missing", "created": 0, "updated": 0}

    base = base_url.rstrip("/")
    if "/api/" in base and "/resources/employees/employees" in base:
        url = base
    else:
        url = f"{base}/api/2026-01-01/resources/employees/employees"
    params = {"only_active": "false"}
    if company_id:
        params["company_id"] = company_id

    try:
        with httpx.Client(timeout=30.0) as client:
            items: list[dict] = []
            cursor: str | None = None

            while True:
                req_params = dict(params)
                if cursor:
                    req_params["cursor"] = cursor

                resp = client.get(
                    url,
                    params=req_params,
                    headers={
                        "x-api-key": token,
                        "accept": "application/json",
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
                page_items = payload.get("data") if isinstance(payload, dict) else []
                if isinstance(page_items, list):
                    items.extend(page_items)

                meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
                if not meta.get("has_next_page"):
                    break
                cursor = meta.get("end_cursor")
                if not cursor:
                    break
    except Exception as exc:
        logger.exception("Factorial sync failed")
        return {
            "ok": False,
            "message": f"Factorial unavailable, using local cache: {exc}",
            "created": 0,
            "updated": 0,
        }
    if not isinstance(items, list):
        return {"ok": False, "message": "Unexpected Factorial payload", "created": 0, "updated": 0}

    created = 0
    updated = 0
    now = datetime.now(UTC)
    for row in items:
        parsed = _extract_employee(row)
        if not parsed["factorial_employee_id"] or parsed["factorial_employee_id"] == "None":
            continue

        employee = db.query(Employee).filter_by(factorial_employee_id=parsed["factorial_employee_id"]).first()
        if not employee:
            employee = Employee(**parsed, last_synced_at=now)
            db.add(employee)
            created += 1
        else:
            employee.first_name = parsed["first_name"]
            employee.last_name = parsed["last_name"]
            employee.email = parsed["email"]
            employee.location = parsed["location"]
            employee.cost_center = parsed["cost_center"]
            employee.is_active = parsed["is_active"]
            employee.last_synced_at = now
            updated += 1

    db.commit()
    return {"ok": True, "message": "Sync completed", "created": created, "updated": updated}
