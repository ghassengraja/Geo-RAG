from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from app.config import settings
from app.graph.tools.geo_tools import geospatial_calculation_tool, ingest_geospatial_data_tool, ingest_raster_data_tool
from app.graph.tools.ltm_tools import fetch_ltm_context_tool

# Initialize the Gemini Model
llm = ChatGoogleGenerativeAI(
    model="gemma-4-26b-a4b-it",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.2,
    streaming=True
)

# Bind tools to the model
tools = [fetch_ltm_context_tool, geospatial_calculation_tool, ingest_geospatial_data_tool, ingest_raster_data_tool]
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a Principal Enterprise AI Architect and Geospatial Analyst. 
You act as the Supervisor Orchestrator in a Multi-Agent Geospatial RAG system.

You have access to the following tools:
1. `fetch_ltm_context_tool`: Use this to remember past user interactions, preferences, or episodic memories stored in the PostGIS database. If the user mentions a location or asks "what did we do last time", use this tool.
2. `geospatial_calculation_tool`: Use this to route heavy data calculation tasks (like spatial intersects, counts, or aggregation) to the Spark & GeoMesa Sub-Agent. 
3. `ingest_geospatial_data_tool`: Use this to ingest VECTOR geospatial files (like GeoJSON) into HBase via GeoMesa CLI. Use this if the user asks you to save or ingest a vector file. The file_path must be the path inside the container (e.g. /datapc/filename).
4. `ingest_raster_data_tool`: Use this to ingest RASTER geospatial files (like GeoTIFFs) into a distributed GeoTrellis catalog in HBase. Use this if the user asks you to ingest a raster or GeoTIFF.


Always evaluate if you need historical context before answering. 
If a user asks a general question, answer it directly.
Be concise and authoritative.
"""

async def supervisor_agent(state: dict):
    """
    The main routing node. Evaluates state and decides whether to respond directly,
    query LTM, or route to the Spark sub-agent via function calls.
    """
    messages = state["messages"]
    
    # Ensure system prompt is present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}
