"""
agent.py — Jarvis ReAct Agent with full system control.

Replaces the fixed 4-node pipeline with a flexible tool-calling loop:
    User → LLM (with all tools) → Tool Call? → Execute → Loop → Final Response

Uses Gemini 2.5 Flash with function calling via LangChain, and binds
every system tool + Tavily web search.
"""

import os

from dotenv import load_dotenv
from typing import TypedDict, Annotated, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langchain_tavily import TavilySearch

from system_tools import ALL_TOOLS

load_dotenv()

# ── System Prompt ────────────────────────────────────────────────────────────

JARVIS_SYSTEM_PROMPT = """You are JARVIS — an advanced AI assistant with full control over the user's Windows PC.

## Your Capabilities
You have access to powerful system tools that let you:
- **Run shell commands** (PowerShell, CMD) to do anything on the system
- **Manage files** — read, write, create, delete, move, search files and directories
- **Open & close applications** — launch any app by name or path
- **Take screenshots** of the screen
- **Control keyboard & mouse** — type text, press hotkeys, click at coordinates
- **Manage the clipboard** — read and write clipboard content
- **Monitor system resources** — CPU, RAM, disk, battery, processes, network
- **Manage windows** — list, focus, minimize, maximize, close windows
- **Control volume** — set level, mute/unmute
- **Search the web** — find up-to-date information online
- **Open URLs** in the default browser
- **Search local documents** — search through the user's ingested local files (PDFs, TXT, DOCX) using a RAG knowledge base
- **Ingest local folders** — scan a folder and index all documents into the knowledge base for future searches

## Behavior Rules
1. **Be proactive**: When the user asks to do something, just do it. Don't ask for confirmation unless the action is destructive (deleting files, killing processes, etc.)
2. **Be precise**: Use the right tool for the job. For file content, use read_file/write_file. For system commands, use run_shell_command or run_powershell.
3. **Be informative**: After performing an action, confirm what you did and report the result.
4. **Be safe**: Never run commands that could damage the system (formatting drives, deleting system files, modifying boot config). These are blocked automatically.
5. **Chain actions**: You can use multiple tools in sequence to accomplish complex tasks. For example, to "find all Python files and count lines", search_files → read_file → report.
6. **Local knowledge first**: When the user asks about their personal documents, notes, or local files, use `search_local_files` BEFORE searching the web. If the knowledge base is empty, suggest ingesting a folder first.
7. **Personality**: You are confident, concise, and a bit witty — like a real AI assistant. You're Jarvis, not a generic chatbot.

## Safety Notes
- Some dangerous commands are automatically blocked for safety.
- File deletions and process kills will execute but are logged.
- Every action you take is logged to an audit file for transparency.
"""

# ── Agent State ──────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ── Build the Agent ──────────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    """
    Construct the Jarvis ReAct agent graph (uncompiled).

    The graph has two nodes:
        1. 'agent' — calls the LLM with the full message history + tools
        2. 'tools' — executes whichever tool the LLM requested

    The conditional edge after 'agent' checks:
        - If the LLM made tool calls → route to 'tools'
        - If the LLM gave a final text response → END
    """

    # Assemble the full tool belt
    web_search = TavilySearch(
        max_results=5,
        description="Search the web for current information. Use when you need up-to-date data, news, or facts."
    )
    all_tools = [web_search] + ALL_TOOLS

    # Initialize the brain with tools bound
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
    ).bind_tools(all_tools)

    # Node 1: Call the LLM
    def agent_node(state: AgentState):
        """Invoke the LLM with the full conversation + system prompt."""
        messages = state["messages"]

        # Prepend system prompt if not already there
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=JARVIS_SYSTEM_PROMPT)] + messages

        response = llm.invoke(messages)
        return {"messages": [response]}

    # Node 2: Execute tools (LangGraph prebuilt)
    tool_node = ToolNode(all_tools)

    # Routing logic
    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        """Route to tools if the LLM made tool calls, else end."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "__end__"

    # Build the graph
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
    graph.add_edge("tools", "agent")  # After tool execution, go back to LLM

    return graph


# Export the uncompiled graph (server.py compiles it with checkpointer)
workflow = build_agent_graph()


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    from langgraph.checkpoint.memory import MemorySaver
    from langchain_core.messages import HumanMessage

    app = workflow.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-session"}}

    print("🤖 JARVIS is online. Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = app.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

        # Get the last AI message
        ai_message = result["messages"][-1]
        print(f"\nJarvis: {ai_message.content}\n")
