from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import json
import logging

from app.graph.workflow import app_graph
from app.db.ltm_repository import insert_episode
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from app.config import settings

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
    Triggers session summarization and saves it to LTM (PostGIS).
    """
    logger.info(f"Closing session {session_id} and summarizing for LTM...")
    
    # 1. Retrieve STM history from the LangGraph checkpointer
    config = {"configurable": {"thread_id": session_id}}
    state = app_graph.get_state(config)
    
    if not state or not state.values or "messages" not in state.values:
        raise HTTPException(status_code=404, detail="Session history not found.")
        
    messages = state.values["messages"]
    conversation_text = "\n".join([f"{m.type}: {m.content}" for m in messages if isinstance(m.content, str)])
    
    # 2. Use Gemini to Summarize and Extract Bounding Box
    summarizer_llm = ChatGoogleGenerativeAI(
        model="gemma-4-26b-a4b-it",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0
    )
    
    prompt = f"""
    Analyze the following conversation history and provide a concise summary of the user's preferences, 
    the spatial analyses performed, and the outcomes. 
    Also, if any specific geographic locations, bounding boxes, or points were discussed, 
    extract a single representative GeoJSON geometry (Point or Polygon) that best represents the episode.
    If no location was discussed, return null for geometry.
    
    Return exactly in this JSON format:
    {{
        "summary": "...",
        "geojson_geometry": {{...}} or null
    }}
    
    Conversation:
    {conversation_text}
    """
    
    # We enforce JSON output
    response = await summarizer_llm.ainvoke(prompt)
    try:
        # Clean markdown formatting if present
        raw_json = response.content.replace("```json\n", "").replace("```", "").strip()
        result = json.loads(raw_json)
        summary = result.get("summary", "No summary generated.")
        geojson_geom = result.get("geojson_geometry")
        if geojson_geom:
            geojson_geom = json.dumps(geojson_geom) # Convert dict to string for Postgres ST_GeomFromGeoJSON
    except Exception as e:
        logger.error(f"Failed to parse LLM summarizer output: {e}")
        summary = "Session closed, but summarization parse failed."
        geojson_geom = None

    # 3. Generate Semantic Embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2", 
        google_api_key=settings.GOOGLE_API_KEY
    )
    vector = await embeddings.aembed_query(summary)
    
    # 4. Insert into LTM (PostGIS)
    await insert_episode(
        session_id=session_id,
        summary=summary,
        embedding=vector,
        geojson_geometry=geojson_geom
    )
    
    return {"status": "success", "message": f"Session {session_id} committed to LTM."}
