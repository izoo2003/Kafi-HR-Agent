"""APScheduler jobs for in-app KPI reminders (Asia/Karachi 18:00 and 18:20)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_scheduler = None


def start_kpi_reminder_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed — KPI reminder jobs disabled")
        return

    from app.core.db import get_session_factory
    from app.services import notification_service

    scheduler = BackgroundScheduler(timezone="Asia/Karachi")

    def _incomplete() -> None:
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            try:
                n = notification_service.run_kpi_incomplete_reminders(db)
                logger.info("KPI incomplete reminders created: %s", n)
            except Exception:  # noqa: BLE001
                logger.exception("KPI incomplete reminder job failed")
                db.rollback()

    def _at_risk() -> None:
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            try:
                n = notification_service.run_kpi_at_risk_reminders(db)
                logger.info("KPI at-risk reminders created: %s", n)
            except Exception:  # noqa: BLE001
                logger.exception("KPI at-risk reminder job failed")
                db.rollback()

    scheduler.add_job(
        _incomplete,
        CronTrigger(hour=18, minute=0, timezone="Asia/Karachi"),
        id="kpi_incomplete_1800",
        replace_existing=True,
    )
    scheduler.add_job(
        _at_risk,
        CronTrigger(hour=18, minute=20, timezone="Asia/Karachi"),
        id="kpi_at_risk_1820",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("KPI reminder scheduler started (Asia/Karachi 18:00 / 18:20)")


def stop_kpi_reminder_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
