from datetime import date
from email.message import EmailMessage
import logging
import smtplib
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.config import get_settings
from app.models import Certification, AlertLog, AlertSetting, User
from app.services.certifications import status_for_expiry

logger = logging.getLogger(__name__)


def _parse_thresholds(csv_text: str) -> list[int]:
    vals = []
    for part in csv_text.split(","):
        part = part.strip()
        if part.isdigit():
            vals.append(int(part))
    return sorted(set(vals), reverse=True)


def _setting_for_cert(db: Session, cert_type: str) -> AlertSetting | None:
    row = db.query(AlertSetting).filter_by(cert_type=cert_type).first()
    if row:
        return row
    return db.query(AlertSetting).filter(AlertSetting.cert_type.is_(None)).first()


def _admin_emails(db: Session) -> list[str]:
    return [u.email for u in db.query(User).filter_by(role="admin", is_active=True).all() if u.email]


def _smtp_config(db: Session) -> dict:
    settings = get_settings()
    return {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "user": settings.smtp_user,
        "password": settings.smtp_password,
        "from": settings.smtp_from,
        "tls": settings.smtp_tls,
    }


def _send_email(recipients: list[str], subject: str, body: str, smtp_cfg: dict) -> None:
    if not recipients or not smtp_cfg.get("host") or not smtp_cfg.get("from"):
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_cfg["from"]
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    with smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=10) as server:
        if smtp_cfg["tls"]:
            server.starttls()
        if smtp_cfg.get("user"):
            server.login(smtp_cfg["user"], smtp_cfg["password"])
        server.send_message(msg)


def _send_webhook(url: str, payload: dict) -> None:
    if not url:
        return
    with httpx.Client(timeout=10.0) as client:
        client.post(url, json=payload)


def run_alerts(db: Session) -> dict:
    today = date.today()
    certs = db.query(Certification).join(Certification.employee).filter(
        or_(Certification.expiry_date >= today, Certification.expiry_date < today)
    ).all()
    sent_count = 0
    smtp_cfg = _smtp_config(db)
    settings = get_settings()

    for cert in certs:
        status = status_for_expiry(cert.expiry_date)
        days_left = (cert.expiry_date - today).days

        rule = _setting_for_cert(db, cert.cert_type)
        if not rule:
            thresholds = [90, 60, 30, 14, 7, 1]
            email_enabled = True
            webhook_enabled = False
            recipients = []
        else:
            thresholds = _parse_thresholds(rule.thresholds_csv)
            email_enabled = rule.email_enabled
            webhook_enabled = rule.webhook_enabled
            recipients = [x.strip() for x in rule.recipient_emails.split(",") if x.strip()]

        recipients = sorted(set(recipients + _admin_emails(db)))

        for threshold in thresholds:
            if days_left == threshold or (status == "expired" and threshold == 1):
                already = db.query(AlertLog).filter_by(
                    certification_id=cert.id,
                    threshold_days=threshold,
                ).first()
                if already:
                    continue

                subject = f"[Formazione] {cert.title} - {cert.employee.first_name} {cert.employee.last_name}"
                body = (
                    f"Certificato: {cert.title}\n"
                    f"Tipo: {cert.cert_type}\n"
                    f"Dipendente: {cert.employee.first_name} {cert.employee.last_name}\n"
                    f"Scadenza: {cert.expiry_date.isoformat()}\n"
                    f"Stato: {status}\n"
                    f"Giorni alla scadenza: {days_left}\n"
                )

                try:
                    if email_enabled:
                        _send_email(recipients, subject, body, smtp_cfg)
                    if webhook_enabled:
                        _send_webhook(settings.webhook_url, {
                            "certification_id": cert.id,
                            "employee_id": cert.employee_id,
                            "threshold": threshold,
                            "days_left": days_left,
                            "status": status,
                        })
                except Exception:
                    logger.exception("Alert dispatch failed")
                    continue

                db.add(AlertLog(certification_id=cert.id, threshold_days=threshold))
                db.commit()
                sent_count += 1

    return {"sent": sent_count}
