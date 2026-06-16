from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import json
import logging

from app.ai.supervisor import app_graph
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


logger = logging.getLogger(__name__)
router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str
    user_input: str

class CloseSessionRequest(BaseModel):
    pass # we get session_id from path

@router.post("/agent/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streams LangGraph execution events and LLM tokens via Server-Sent Events (SSE).
    """
    config = {"configurable": {"thread_id": request.session_id}}
    input_message = HumanMessage(content=request.user_input)

    async def event_generator():
        try:
            # Using v2 stream API for granular event visibility
            async for event in app_graph.astream_events(
                {"messages": [input_message]},
                config=config,
                version="v2"
            ):
                kind = event["event"]
                
                # Stream token generation
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield {
                            "event": "token",
                            "data": json.dumps({"text": content})
                        }
                        
                # Stream Agent Tool usage transitions
                elif kind == "on_tool_start":
                    yield {
                        "event": "status",
                        "data": json.dumps({"message": f"Sub-agent initializing: {event['name']}..."})
                    }
                elif kind == "on_tool_end":
                    yield {
                        "event": "status",
                        "data": json.dumps({"message": f"Tool {event['name']} completed."})
                    }
                    
        except Exception as e:
            logger.error(f"Error during stream: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "Internal Server Error during execution."})
            }

    return EventSourceResponse(event_generator())


@router.post("/session/{session_id}/close")
async def close_session(session_id: str):
    """
    Triggers session summarization and saves it to LTM (PostGIS/PGVector).
    Delegates entirely to the langgraph supervisor and memory agent.
    """
    logger.info(f"Closing session {session_id} and summarizing for LTM via agents...")
    
    config = {"configurable": {"thread_id": session_id}}
    
    prompt = """
    SYSTEM INSTRUCTION: The user session is now closing. 
    Review the recent conversation history. Extract any newly discussed facts, details, or events about specific Regions or Places.
    Once extracted, route to the memory agent to save them to the geospatial episodic memory using your strict deduplication workflow.
    """
    
    try:
        await app_graph.ainvoke({"messages": [HumanMessage(content=prompt)]}, config)
        return {"status": "success", "message": "Session closed and memory updated."}
    except Exception as e:
        logger.error(f"Failed to close session and update memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to close session.")
