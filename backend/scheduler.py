from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import SessionLocal
from backend.services.report_service import get_or_generate_monthly_report

scheduler = BackgroundScheduler()


def generate_previous_month_report_job():
    """Job to generate previous month report automatically."""
    db = SessionLocal()
    try:
        today = date.today()
        # Get previous month
        if today.month == 1:
            prev_month_str = f"{today.year - 1}-12"
        else:
            prev_month_str = f"{today.year}-{today.month - 1:02d}"

        print(f"[Scheduler] Running automated month-end report generation for: {prev_month_str}")
        get_or_generate_monthly_report(db, prev_month_str, force_refresh=True)
    except Exception as e:
        print(f"[Scheduler] Monthly report generation job error: {e}")
    finally:
        db.close()


def start_scheduler():
    # Schedule to run on 1st day of every month at 00:05
    scheduler.add_job(
        generate_previous_month_report_job,
        trigger="cron",
        day=1,
        hour=0,
        minute=5,
        id="monthly_report_job",
        replace_existing=True
    )
    if not scheduler.running:
        scheduler.start()
        print("[Scheduler] APScheduler started successfully.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("[Scheduler] APScheduler stopped.")
