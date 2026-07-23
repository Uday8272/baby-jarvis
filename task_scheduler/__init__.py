
'''
scheduler -- time-based task scheduling and event-driven routines for jarvis. 
provides langchain tool that let the react agent schedule future actions, manager recurring routines, and watch folders for changes
''' 

from task_scheduler.tools import cancel_scheduled_task
from task_scheduler.tools import (
    schedule_task, 
    schedule_cron_task, 
    list_scheduled_tasks, 
    watch_folder, 
    stop_watching_folder, 
) 

SCHEDULER_TOOLS = [
    schedule_task, 
    schedule_cron_task, 
    list_scheduled_tasks, 
    cancel_scheduled_task,
    watch_folder, 
    stop_watching_folder, 
] 



