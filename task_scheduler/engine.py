
"""
engine.py — Core scheduler engine for Jarvis.

Wraps APScheduler's AsyncIOScheduler with:
  - SQLite job store for persistence across restarts
  - Methods to add/remove/list/pause/resume jobs
  - Singleton pattern so tools and server share one instance
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR


# ── Persistence ──────────────────────────────────────────────────────────────
# Store scheduled jobs in SQLite so they survive server restarts.

DATA_DIR = Path(os.getenv("JARVIS_DATA_DIR", "./data"))
SCHEDULER_DB_PATH = DATA_DIR / "scheduler.db"


# ── Singleton Scheduler Instance ─────────────────────────────────────────────

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """
    Return the global scheduler instance.
    Creates it on first call (lazy init) but does NOT start it —
    starting is done in the server lifespan.
    """
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    # ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    job_store = SQLAlchemyJobStore(url=f"sqlite:///{SCHEDULER_DB_PATH}")

    _scheduler = AsyncIOScheduler(
        jobstores={"default": job_store},
        job_defaults={
            "coalesce": True,           # if multiple misfires, run once
            "max_instances": 1,         # don't overlap same job
            "misfire_grace_time": 60,   # allow 60s late execution
        },
    )

    # listen for job events (for logging)
    _scheduler.add_listener(_on_job_executed, EVENT_JOB_EXECUTED)
    _scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)

    return _scheduler


def _on_job_executed(event):
    """Log successful job executions."""
    print(f"[SCHEDULER] Job '{event.job_id}' executed successfully.")


def _on_job_error(event):
    """Log job execution errors."""
    print(f"[SCHEDULER] Job '{event.job_id}' raised an error: {event.exception}")


# ── Public API ───────────────────────────────────────────────────────────────

def add_one_shot_task(
    job_id: str,
    run_at: datetime,
    task_description: str,
) -> str:
    """
    Schedule a one-shot task that fires once at `run_at`.

    Args:
        job_id: Unique identifier for the job.
        run_at: When to fire (datetime, should be in the future).
        task_description: What the job should do (stored as job arg).

    Returns:
        Confirmation string.
    """
    scheduler = get_scheduler()

    # import here to avoid circular imports
    from scheduler.jobs import execute_scheduled_task

    scheduler.add_job(
        execute_scheduled_task,
        trigger=DateTrigger(run_date=run_at),
        id=job_id,
        name=task_description,
        args=[task_description],
        replace_existing=True,
    )

    return f"Scheduled one-shot task '{job_id}' for {run_at.strftime('%Y-%m-%d %H:%M:%S')}"


def add_interval_task(
    job_id: str,
    task_description: str,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """
    Schedule a recurring task that repeats at a fixed interval.

    Args:
        job_id: Unique identifier.
        task_description: What the job should do.
        hours/minutes/seconds: Interval between runs.

    Returns:
        Confirmation string.
    """
    scheduler = get_scheduler()
    from scheduler.jobs import execute_scheduled_task

    scheduler.add_job(
        execute_scheduled_task,
        trigger=IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds),
        id=job_id,
        name=task_description,
        args=[task_description],
        replace_existing=True,
    )

    interval_parts = []
    if hours:
        interval_parts.append(f"{hours}h")
    if minutes:
        interval_parts.append(f"{minutes}m")
    if seconds:
        interval_parts.append(f"{seconds}s")
    interval_str = " ".join(interval_parts) or "0s"

    return f"Scheduled recurring task '{job_id}' every {interval_str}"


def add_cron_task(
    job_id: str,
    task_description: str,
    cron_expression: str,
) -> str:
    """
    Schedule a cron-based task (e.g., "every weekday at 9 AM").

    Args:
        job_id: Unique identifier.
        task_description: What the job should do.
        cron_expression: Standard 5-field cron string
                         (minute hour day_of_month month day_of_week).
                         Examples: "0 9 * * *" = 9 AM daily,
                                   "30 8 * * 1-5" = 8:30 AM weekdays.

    Returns:
        Confirmation string.
    """
    scheduler = get_scheduler()
    from scheduler.jobs import execute_scheduled_task

    # parse cron expression: "minute hour day month day_of_week"
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        return f"Error: Invalid cron expression '{cron_expression}'. Expected 5 fields: minute hour day month day_of_week"

    minute, hour, day, month, day_of_week = parts

    scheduler.add_job(
        execute_scheduled_task,
        trigger=CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        ),
        id=job_id,
        name=task_description,
        args=[task_description],
        replace_existing=True,
    )

    return f"Scheduled cron task '{job_id}' with schedule '{cron_expression}'"


def remove_task(job_id: str) -> str:
    """Remove a scheduled task by ID."""
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        return f"Cancelled task '{job_id}'."
    except Exception as e:
        return f"Error cancelling task '{job_id}': {e}"


def get_all_tasks() -> list[dict]:
    """
    Return a list of all pending scheduled tasks.

    Each dict contains: id, name, next_run_time, trigger.
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    tasks = []
    for job in jobs:
        tasks.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else "paused",
            "trigger": str(job.trigger),
        })

    return tasks


def pause_task(job_id: str) -> str:
    """Pause a scheduled task (it won't fire until resumed)."""
    scheduler = get_scheduler()
    try:
        scheduler.pause_job(job_id)
        return f"Paused task '{job_id}'."
    except Exception as e:
        return f"Error pausing task '{job_id}': {e}"


def resume_task(job_id: str) -> str:
    """Resume a paused scheduled task."""
    scheduler = get_scheduler()
    try:
        scheduler.resume_job(job_id)
        return f"Resumed task '{job_id}'."
    except Exception as e:
        return f"Error resuming task '{job_id}': {e}"
