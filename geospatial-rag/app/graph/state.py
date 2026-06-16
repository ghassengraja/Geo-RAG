from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Represents the state of our LangGraph workflow.
    `messages` holds the short-term memory (STM) thread history.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
