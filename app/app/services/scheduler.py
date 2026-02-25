from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from app.db.session import SessionLocal
from app.core.config import get_settings
from app.services.factorial import sync_factorial_employees
from app.services.alerts import run_alerts

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _job_sync_factorial() -> None:
    db = SessionLocal()
    try:
        result = sync_factorial_employees(db)
        logger.info("factorial_sync", extra={"result": result})
    finally:
        db.close()


def _job_alerts() -> None:
    db = SessionLocal()
    try:
        result = run_alerts(db)
        logger.info("alert_job", extra={"result": result})
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return

    minute, hour, day, month, dow = settings.factorial_sync_cron.split(" ")
    scheduler.add_job(
        _job_sync_factorial,
        trigger=CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow),
        id="factorial_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _job_alerts,
        trigger=CronTrigger(hour=3, minute=15),
        id="cert_alerts",
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
