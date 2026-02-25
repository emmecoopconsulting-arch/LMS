from datetime import date, timedelta
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Employee, Certification, Attachment, AlertSetting
from app.schemas.api import CertificationCreate, SettingsUpdate
from app.services.auth import get_current_user, require_role
from app.services.certifications import status_for_expiry
from app.services.files import store_upload
from app.services.factorial import sync_factorial_employees
from app.services.settings_store import set_setting, get_setting
from app.services.audit import write_audit
from app.core.config import get_settings

router = APIRouter(prefix="/api")


@router.get("/employees")
def api_employees(
    q: str = "",
    active: bool | None = None,
    location: str = "",
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Employee)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Employee.first_name.ilike(like) | Employee.last_name.ilike(like) | Employee.email.ilike(like)
        )
    if active is not None:
        query = query.filter(Employee.is_active == active)
    if location:
        query = query.filter(Employee.location == location)

    rows = query.order_by(Employee.last_name.asc()).all()
    return [
        {
            "id": e.id,
            "factorial_employee_id": e.factorial_employee_id,
            "first_name": e.first_name,
            "last_name": e.last_name,
            "email": e.email,
            "location": e.location,
            "cost_center": e.cost_center,
            "is_active": e.is_active,
        }
        for e in rows
    ]


@router.get("/employees/{employee_id}/certifications")
def api_employee_certifications(
    employee_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    certs = db.query(Certification).filter_by(employee_id=employee_id).all()
    return [
        {
            "id": c.id,
            "cert_type": c.cert_type,
            "title": c.title,
            "provider": c.provider,
            "issued_date": c.issued_date,
            "expiry_date": c.expiry_date,
            "status": status_for_expiry(c.expiry_date),
        }
        for c in certs
    ]


@router.post("/employees/{employee_id}/certifications")
def api_create_certification(
    employee_id: int,
    payload: CertificationCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("manager")),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    cert = Certification(
        employee_id=employee_id,
        cert_type=payload.cert_type,
        title=payload.title,
        provider=payload.provider,
        issued_date=payload.issued_date,
        expiry_date=payload.expiry_date,
        notes=payload.notes,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    write_audit(db, user.id, "create", "certification", str(cert.id), {"employee_id": employee_id})
    return {"id": cert.id}


@router.put("/certifications/{cert_id}")
def api_update_certification(
    cert_id: int,
    payload: CertificationCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("manager")),
):
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    cert.cert_type = payload.cert_type
    cert.title = payload.title
    cert.provider = payload.provider
    cert.issued_date = payload.issued_date
    cert.expiry_date = payload.expiry_date
    cert.notes = payload.notes
    cert.updated_by = user.id
    db.commit()
    write_audit(db, user.id, "update", "certification", str(cert.id), {"employee_id": cert.employee_id})
    return {"ok": True}


@router.delete("/certifications/{cert_id}")
def api_delete_certification(
    cert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("manager")),
):
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    employee_id = cert.employee_id
    db.delete(cert)
    db.commit()
    write_audit(db, user.id, "delete", "certification", str(cert_id), {"employee_id": employee_id})
    return {"ok": True}


@router.post("/certifications/{cert_id}/attachments")
def api_upload_attachment(
    cert_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("manager")),
):
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    created = []
    for f in files:
        path, size, checksum = store_upload(f)
        row = Attachment(
            certification_id=cert_id,
            original_filename=f.filename or "file",
            stored_path=path,
            mime_type=f.content_type or "application/octet-stream",
            file_size=size,
            checksum_sha256=checksum,
            uploaded_by=user.id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        write_audit(db, user.id, "create", "attachment", str(row.id), {"certification_id": cert_id})
        created.append({"id": row.id, "filename": row.original_filename})
    return created


@router.delete("/attachments/{attachment_id}")
def api_delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("manager")),
):
    row = db.get(Attachment, attachment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")
    certification_id = row.certification_id
    db.delete(row)
    db.commit()
    write_audit(db, user.id, "delete", "attachment", str(attachment_id), {"certification_id": certification_id})
    return {"ok": True}


@router.get("/certifications")
def api_certifications(
    cert_type: str = "",
    status: str = "",
    location: str = "",
    expires_within_days: int = 0,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    today = date.today()
    query = db.query(Certification).join(Certification.employee)
    if cert_type:
        query = query.filter(Certification.cert_type == cert_type)
    if location:
        query = query.filter(Employee.location == location)
    if expires_within_days > 0:
        query = query.filter(Certification.expiry_date <= today + timedelta(days=expires_within_days))

    rows = query.order_by(Certification.expiry_date.asc()).all()
    response = []
    for c in rows:
        computed = status_for_expiry(c.expiry_date)
        if status and computed != status:
            continue
        response.append(
            {
                "id": c.id,
                "employee_id": c.employee_id,
                "employee": f"{c.employee.first_name} {c.employee.last_name}",
                "cert_type": c.cert_type,
                "title": c.title,
                "expiry_date": c.expiry_date,
                "status": computed,
            }
        )
    return response


@router.get("/admin/settings")
def api_get_settings(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    cfg = get_settings()
    base = db.query(AlertSetting).filter(AlertSetting.cert_type.is_(None)).first()
    return {
        "factorial_base_url": get_setting(db, "factorial_base_url", cfg.factorial_base_url),
        "factorial_api_token": get_setting(db, "factorial_api_token", cfg.factorial_api_token),
        "factorial_company_id": get_setting(db, "factorial_company_id", cfg.factorial_company_id),
        "thresholds_csv": base.thresholds_csv if base else "90,60,30,14,7,1",
        "recipient_emails": base.recipient_emails if base else "",
        "email_enabled": base.email_enabled if base else True,
        "webhook_enabled": base.webhook_enabled if base else False,
    }


@router.post("/admin/settings")
def api_update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    set_setting(db, "factorial_base_url", payload.factorial_base_url)
    set_setting(db, "factorial_api_token", payload.factorial_api_token)
    set_setting(db, "factorial_company_id", payload.factorial_company_id)

    rule = db.query(AlertSetting).filter(AlertSetting.cert_type.is_(None)).first()
    if not rule:
        rule = AlertSetting(cert_type=None)
        db.add(rule)
    rule.thresholds_csv = payload.thresholds_csv
    rule.recipient_emails = payload.recipient_emails
    rule.email_enabled = payload.email_enabled
    rule.webhook_enabled = payload.webhook_enabled
    db.commit()
    return {"ok": True}


@router.post("/admin/sync/factorial")
def api_sync_factorial(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    return sync_factorial_employees(db)
