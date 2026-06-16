from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState
from app.graph.agents import supervisor_agent, tools

# 1. Define the tools node
tool_node = ToolNode(tools)

def should_continue(state: AgentState):
    """
    Conditional edge logic: checks if the supervisor called a tool.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If there is a tool call, route to the tools node
    if last_message.tool_calls:
        return "tools"
    
    # Otherwise, finish
    return END

# 2. Build the Graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("tools", tool_node)

# Add edges
workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

# Return from tools back to supervisor to evaluate the tool output
workflow.add_edge("tools", "supervisor")

# 3. Compile with native Short-Term Memory (STM) Saver
memory_saver = MemorySaver()
app_graph = workflow.compile(checkpointer=memory_saver)
