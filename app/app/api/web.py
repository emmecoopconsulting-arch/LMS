from datetime import date, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db, SessionLocal
from app.models import User, Employee, Certification, Attachment, AlertSetting
from app.core.security import verify_password, hash_password
from app.core.csrf import ensure_csrf_token, validate_csrf
from app.core.rate_limit import LoginRateLimiter
from app.core.config import get_settings
from app.services.auth import get_current_user, require_role
from app.services.certifications import status_for_expiry
from app.services.files import store_upload
from app.services.factorial import sync_factorial_employees
from app.services.audit import write_audit
from app.services.settings_store import get_setting, set_setting

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
rate_limiter = LoginRateLimiter(
    max_attempts=get_settings().login_rate_limit_attempts,
    window_seconds=get_settings().login_rate_limit_window_seconds,
)


def _render(request: Request, template: str, context: dict):
    base = {
        "request": request,
        "current_user": None,
        "csrf_token": ensure_csrf_token(request),
    }
    user_id = request.session.get("user_id")
    if user_id:
        db = SessionLocal()
        try:
            base["current_user"] = db.get(User, user_id)
        finally:
            db.close()
    base.update(context)
    return templates.TemplateResponse(template, base)


@router.get("/login")
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return _render(request, "auth/login.html", {"error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    client_ip = request.client.host if request.client else "unknown"
    if rate_limiter.is_limited(client_ip):
        return _render(request, "auth/login.html", {"error": "Troppi tentativi. Riprova più tardi."})

    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        rate_limiter.add_attempt(client_ip)
        return _render(request, "auth/login.html", {"error": "Credenziali non valide"})

    rate_limiter.reset(client_ip)
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today = date.today()
    certs = db.query(Certification).all()
    expired = sum(1 for c in certs if c.expiry_date < today)
    expiring = sum(1 for c in certs if 0 <= (c.expiry_date - today).days <= 30)

    upcoming = []
    for days in [30, 60, 90]:
        lim = today + timedelta(days=days)
        items = (
            db.query(Certification)
            .join(Certification.employee)
            .filter(Certification.expiry_date >= today, Certification.expiry_date <= lim)
            .order_by(Certification.expiry_date.asc())
            .limit(20)
            .all()
        )
        upcoming.append((days, items))

    return _render(
        request,
        "dashboard/index.html",
        {
            "expired": expired,
            "expiring": expiring,
            "upcoming": upcoming,
            "status_for_expiry": status_for_expiry,
        },
    )


@router.get("/employees")
def employee_list(
    request: Request,
    q: str = "",
    location: str = "",
    active: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Employee)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Employee.first_name.ilike(like) | Employee.last_name.ilike(like) | Employee.email.ilike(like)
        )
    if location:
        query = query.filter(Employee.location == location)
    if active in {"true", "false"}:
        query = query.filter(Employee.is_active == (active == "true"))

    employees = query.order_by(Employee.last_name.asc(), Employee.first_name.asc()).all()
    locations = [x[0] for x in db.query(Employee.location).distinct().all() if x[0]]
    return _render(
        request,
        "employees/list.html",
        {"employees": employees, "locations": locations, "q": q, "location": location, "active": active},
    )


@router.get("/employees/{employee_id}")
def employee_detail(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404)
    certs = (
        db.query(Certification)
        .filter_by(employee_id=employee.id)
        .order_by(Certification.expiry_date.asc())
        .all()
    )
    return _render(
        request,
        "employees/detail.html",
        {"employee": employee, "certifications": certs, "status_for_expiry": status_for_expiry},
    )


@router.post("/employees/{employee_id}/certifications")
def create_certification_web(
    employee_id: int,
    request: Request,
    cert_type: str = Form(...),
    title: str = Form(...),
    provider: str = Form(""),
    issued_date: str = Form(""),
    expiry_date: str = Form(...),
    notes: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    validate_csrf(request, csrf_token)
    cert = Certification(
        employee_id=employee_id,
        cert_type=cert_type,
        title=title,
        provider=provider or None,
        issued_date=date.fromisoformat(issued_date) if issued_date else None,
        expiry_date=date.fromisoformat(expiry_date),
        notes=notes or None,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(cert)
    db.commit()
    write_audit(db, user.id, "create", "certification", str(cert.id), {"employee_id": employee_id})
    return RedirectResponse(f"/employees/{employee_id}", status_code=303)


@router.post("/certifications/{cert_id}/attachments")
def upload_attachment_web(
    cert_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    validate_csrf(request, csrf_token)
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404)

    for item in files:
        path, size, checksum = store_upload(item)
        att = Attachment(
            certification_id=cert.id,
            original_filename=item.filename or "file",
            stored_path=path,
            mime_type=item.content_type or "application/octet-stream",
            file_size=size,
            checksum_sha256=checksum,
            uploaded_by=user.id,
        )
        db.add(att)
        db.commit()
        write_audit(db, user.id, "create", "attachment", str(att.id), {"certification_id": cert.id})

    return RedirectResponse(f"/employees/{cert.employee_id}", status_code=303)


@router.post("/certifications/{cert_id}/update")
def update_certification_web(
    cert_id: int,
    request: Request,
    title: str = Form(...),
    cert_type: str = Form(...),
    provider: str = Form(""),
    issued_date: str = Form(""),
    expiry_date: str = Form(...),
    notes: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    validate_csrf(request, csrf_token)
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404)
    cert.title = title
    cert.cert_type = cert_type
    cert.provider = provider or None
    cert.issued_date = date.fromisoformat(issued_date) if issued_date else None
    cert.expiry_date = date.fromisoformat(expiry_date)
    cert.notes = notes or None
    cert.updated_by = user.id
    db.commit()
    write_audit(db, user.id, "update", "certification", str(cert.id), {"employee_id": cert.employee_id})
    return RedirectResponse(f"/employees/{cert.employee_id}", status_code=303)


@router.post("/certifications/{cert_id}/delete")
def delete_certification_web(
    cert_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    validate_csrf(request, csrf_token)
    cert = db.get(Certification, cert_id)
    if not cert:
        raise HTTPException(status_code=404)
    employee_id = cert.employee_id
    db.delete(cert)
    db.commit()
    write_audit(db, user.id, "delete", "certification", str(cert_id), {"employee_id": employee_id})
    return RedirectResponse(f"/employees/{employee_id}", status_code=303)


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    att = db.get(Attachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404)
    path = Path(att.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(path=path, filename=att.original_filename, media_type=att.mime_type)


@router.post("/attachments/{attachment_id}/delete")
def delete_attachment_web(
    attachment_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    validate_csrf(request, csrf_token)
    att = db.get(Attachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404)
    employee_id = att.certification.employee_id
    file_path = Path(att.stored_path)
    if file_path.exists():
        file_path.unlink()
    db.delete(att)
    db.commit()
    write_audit(
        db,
        user.id,
        "delete",
        "attachment",
        str(attachment_id),
        {"certification_id": att.certification_id},
    )
    return RedirectResponse(f"/employees/{employee_id}", status_code=303)


@router.get("/certifications")
def certifications_list(
    request: Request,
    cert_type: str = "",
    status: str = "",
    location: str = "",
    days: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today = date.today()
    query = db.query(Certification).join(Certification.employee)
    if cert_type:
        query = query.filter(Certification.cert_type == cert_type)
    if location:
        query = query.filter(Employee.location == location)
    if days > 0:
        query = query.filter(Certification.expiry_date <= today + timedelta(days=days))

    certs = query.order_by(Certification.expiry_date.asc()).all()
    if status:
        certs = [c for c in certs if status_for_expiry(c.expiry_date) == status]

    cert_types = [x[0] for x in db.query(Certification.cert_type).distinct().all() if x[0]]
    locations = [x[0] for x in db.query(Employee.location).distinct().all() if x[0]]
    return _render(
        request,
        "certifications/list.html",
        {
            "certifications": certs,
            "cert_types": cert_types,
            "locations": locations,
            "status_for_expiry": status_for_expiry,
            "filters": {"cert_type": cert_type, "status": status, "location": location, "days": days},
        },
    )


@router.get("/admin/settings")
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    data = {
        "factorial_base_url": get_setting(db, "factorial_base_url", get_settings().factorial_base_url),
        "factorial_api_token": get_setting(db, "factorial_api_token", get_settings().factorial_api_token),
        "factorial_company_id": get_setting(db, "factorial_company_id", get_settings().factorial_company_id),
    }
    rule = db.query(AlertSetting).filter(AlertSetting.cert_type.is_(None)).first()
    if not rule:
        rule = AlertSetting(cert_type=None, thresholds_csv="90,60,30,14,7,1", email_enabled=True, webhook_enabled=False)
        db.add(rule)
        db.commit()

    return _render(request, "admin/settings.html", {"data": data, "rule": rule})


@router.post("/admin/settings")
def settings_update(
    request: Request,
    factorial_base_url: str = Form(""),
    factorial_api_token: str = Form(""),
    factorial_company_id: str = Form(""),
    thresholds_csv: str = Form("90,60,30,14,7,1"),
    recipient_emails: str = Form(""),
    email_enabled: str = Form("off"),
    webhook_enabled: str = Form("off"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    validate_csrf(request, csrf_token)
    set_setting(db, "factorial_base_url", factorial_base_url)
    set_setting(db, "factorial_api_token", factorial_api_token)
    set_setting(db, "factorial_company_id", factorial_company_id)

    rule = db.query(AlertSetting).filter(AlertSetting.cert_type.is_(None)).first()
    if not rule:
        rule = AlertSetting(cert_type=None)
        db.add(rule)
    rule.thresholds_csv = thresholds_csv
    rule.recipient_emails = recipient_emails
    rule.email_enabled = email_enabled == "on"
    rule.webhook_enabled = webhook_enabled == "on"
    db.commit()
    return RedirectResponse("/admin/settings", status_code=303)


@router.post("/admin/sync")
def sync_now(
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    validate_csrf(request, csrf_token)
    sync_factorial_employees(db)
    return RedirectResponse("/employees", status_code=303)


@router.get("/admin/users")
def users_page(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return _render(request, "users/list.html", {"users": users})


@router.post("/admin/users")
def create_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    validate_csrf(request, csrf_token)
    exists = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if exists:
        return RedirectResponse("/admin/users", status_code=303)
    user = User(full_name=full_name, email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)
