
"""
tools.py — LangChain tools for Jarvis scheduler and file watcher.

These tools are registered in ALL_TOOLS so the Jarvis ReAct agent
can schedule tasks, manage routines, and watch folders through
natural language commands.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool


# ── Scheduling Tools ─────────────────────────────────────────────────────────

@tool
def schedule_task(task_description: str, delay_minutes: int = 0, repeat_every_minutes: int = 0) -> str:
    """Schedule a task for Jarvis to execute in the future.

    Use this for simple time-based scheduling like reminders, delayed actions,
    or repeating tasks.

    Args:
        task_description: What Jarvis should do when the task fires.
            Be specific — this will be sent to Jarvis as a command.
            Examples:
              - "Open Chrome and navigate to gmail.com"
              - "Run get_system_stats and report the results"
              - "Remind the user to take a break"
        delay_minutes: How many minutes from now to first execute the task.
            Set to 0 for immediate first execution (only useful with repeat).
            Examples: 30 (in 30 minutes), 60 (in 1 hour), 1440 (in 24 hours).
        repeat_every_minutes: If set to a positive number, the task will
            repeat at this interval (in minutes). Set to 0 for a one-shot task.
            Examples: 60 (every hour), 120 (every 2 hours), 1440 (every day).

    Returns:
        A confirmation message with the task ID and schedule details.
    """
    from task_scheduler.engine import add_one_shot_task, add_interval_task

    # generate a human-readable job ID
    short_id = uuid.uuid4().hex[:6]
    job_id = f"task-{short_id}"

    if repeat_every_minutes > 0:
        # recurring task
        result = add_interval_task(
            job_id=job_id,
            task_description=task_description,
            minutes=repeat_every_minutes,
        )
    else:
        # one-shot task
        if delay_minutes <= 0:
            return "Error: For a one-shot task, delay_minutes must be greater than 0."

        run_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        result = add_one_shot_task(
            job_id=job_id,
            run_at=run_at,
            task_description=task_description,
        )

    return result


@tool
def schedule_cron_task(task_description: str, cron_expression: str) -> str:
    """Schedule a cron-based recurring task for Jarvis.

    Use this for tasks that follow a calendar-based schedule like
    "every morning at 9 AM" or "every Sunday at midnight".

    Args:
        task_description: What Jarvis should do when the task fires.
            Be specific. Examples:
              - "Open Outlook and check for new emails"
              - "Take a screenshot and save it as a daily log"
              - "Run disk cleanup using PowerShell"
        cron_expression: A standard 5-field cron expression.
            Format: "minute hour day_of_month month day_of_week"
            Common examples:
              - "0 9 * * *"     → Every day at 9:00 AM
              - "30 8 * * 1-5"  → Weekdays at 8:30 AM
              - "0 0 * * 0"     → Every Sunday at midnight
              - "*/30 * * * *"  → Every 30 minutes
              - "0 9,18 * * *"  → At 9 AM and 6 PM daily

    Returns:
        A confirmation message with the task ID and cron schedule.
    """
    from task_scheduler.engine import add_cron_task

    short_id = uuid.uuid4().hex[:6]
    job_id = f"cron-{short_id}"

    result = add_cron_task(
        job_id=job_id,
        task_description=task_description,
        cron_expression=cron_expression,
    )

    return result


@tool
def list_scheduled_tasks() -> str:
    """List all currently scheduled tasks and routines.

    Shows all pending one-shot tasks, recurring tasks, and cron jobs
    with their IDs, descriptions, next run times, and schedules.

    Use this when the user asks things like:
      - "What tasks do I have scheduled?"
      - "Show my routines"
      - "What's coming up?"

    Returns:
        A formatted list of all scheduled tasks, or a message if none exist.
    """
    from task_scheduler.engine import get_all_tasks

    tasks = get_all_tasks()

    if not tasks:
        return "No tasks are currently scheduled."

    lines = ["📋 **Scheduled Tasks:**\n"]
    for t in tasks:
        lines.append(
            f"  • **{t['name']}**\n"
            f"    ID: `{t['id']}` | Next run: {t['next_run_time']} | Schedule: {t['trigger']}"
        )

    return "\n".join(lines)


@tool
def cancel_scheduled_task(task_id: str) -> str:
    """Cancel a scheduled task by its ID.

    Use this when the user wants to stop a scheduled reminder, routine,
    or recurring task. The task_id can be found using list_scheduled_tasks.

    Args:
        task_id: The ID of the task to cancel (e.g., "task-a1b2c3" or "cron-d4e5f6").

    Returns:
        A confirmation that the task was cancelled, or an error message.
    """
    from task_scheduler.engine import remove_task

    return remove_task(task_id)


# ── File Watcher Tools ───────────────────────────────────────────────────────

@tool
def watch_folder(folder_path: str) -> str:
    """Start monitoring a folder for file system changes (new files, deletions, modifications).

    Use this when the user says things like:
      - "Watch my Downloads folder"
      - "Monitor D:/Projects for changes"
      - "Let me know when new files appear in my Documents"

    The watcher runs in the background. Use list_scheduled_tasks to see active watchers,
    and stop_watching_folder to stop.

    Args:
        folder_path: The absolute path to the folder to watch.
            Examples: "C:/Users/username/Downloads", "D:/Projects"

    Returns:
        Confirmation that the folder is being watched, or an error message.
    """
    from task_scheduler.watcher import start_watching

    return start_watching(folder_path)


@tool
def stop_watching_folder(folder_path: str) -> str:
    """Stop monitoring a folder for file system changes.

    Args:
        folder_path: The path of the folder to stop watching.

    Returns:
        Confirmation that the watcher was stopped, or an error message.
    """
    from task_scheduler.watcher import stop_watching

    return stop_watching(folder_path)


