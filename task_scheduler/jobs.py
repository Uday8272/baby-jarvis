
"""
jobs.py — Job callback functions for the Jarvis scheduler.
When a scheduled task fires, APScheduler calls `execute_scheduled_task()`.
This function bridges the scheduler to the Jarvis agent — it sends the
task description as a message to the agent so Jarvis can reason about
what to do and use his tools.
"""

from langchain_core.messages import content
from pydantic import config
import asyncio 
import uuid 

from langchain_core.messages import HumanMessage 

# reference to the compiled agent 
# this is set by server.py during startup (after the agent is compiled). 
# we store it here so scheduled jobs can invoke the agent 

_agent_app = None 

def set_agent_app(app):
    '''
    called by server.py to provide the compiled agent graph 
    ''' 

    global _agent_app 
    _agent_app = app 

async def execute_scheduled_task(task_description: str) -> None: 

    '''
    called by apschduler when a scheduled job fires
    sends the task description to the jarvis agent as a message, 
    so jarvis can reason about what tyo do and use this tools. 

    Args:
        task_description: Natural language description of what to do.
                          e.g., "Open Gmail in the browser"
                          e.g., "Run a system health check and log results"
    ''' 

    if _agent_app is None:
        print(f"[scheduler] agent not ready. skipping task: {task_description}")
        return 

    # create a unique session for this scheduled execution 
    session_id = f"scheduled-{uuid.uuid4().hex[:8]}" 
    config = {"configurable": {"thread_id": session_id}} 

    # frame the task as a system-initiated instruction 
    prompt = (
        f"[SCHDULED TASK] the following task was scheduled by the user and is now due."
        f"execute it now:\n\n{task_description}"
    ) 

    print(f"\n[SCHEDULER] firing scheduled task: '{task_description}'") 

    try: 
        result = _agent_app.invoke(
            {"message": [HumanMessage(content=prompt)]}, 
            config=config, 
        ) 

        # extract the response 
        ai_message = result["messages"][-1] 
        response = ai_message.content if hasattr(ai_message, "content") else "" 

        # handle list-type content (gemini sometimes returns this) 
        if isinstance(response, list): 
            response = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in response
            ).strip() 

        print(f"[SCHEDULER] task completed. jarvis response: {response[:200]}")

    except Exception as e:
        print(f"[SCHEDULER] task failed: {e}") 
        