from langgraph_supervisor import create_supervisor
from app.ai.llm import get_model
from app.ai.agents import get_vector_agent, get_raster_agent, get_memory_agent
from langgraph.checkpoint.redis import AsyncRedisSaver
import redis.asyncio as redis
from app.config import settings

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=False)
redis_client = redis.Redis(connection_pool=redis_pool)
memory_saver = AsyncRedisSaver(redis_client=redis_client)


def get_supervisor(model=None, checkpointer=None):
    if model is None:
        model = get_model()
        
    vector_agent = get_vector_agent(checkpointer=checkpointer)
    raster_agent = get_raster_agent(checkpointer=checkpointer)
    memory_agent = get_memory_agent(checkpointer=checkpointer)
    
    vector_agent.name = "vector_agent"
    raster_agent.name = "raster_agent"
    memory_agent.name = "memory_agent"
    
    SUPERVISOR_PROMPT = """You are a Principal Enterprise AI Architect and Geospatial Analyst. 
You act as the Supervisor Orchestrator in a Multi-Agent Geospatial RAG system.

You can delegate tasks to the following sub-agents:
- `memory_agent`: Use this to remember past user interactions, preferences, or episodic memories stored in the PostGIS database. If the user mentions a location or asks "what did we do last time", delegate to this agent.
- `vector_agent`: Use this for all vector data operations using GeoMesa (e.g., Shapefiles, GeoJSON, Points, Polygons). Delegate to this agent for spatial intersection queries, counting vector features, or introspecting vector catalogs.
- `raster_agent`: Use this for all raster data operations using GeoTrellis and Spark (e.g., GeoTIFFs, pixel data, imagery). Delegate to this agent for ingesting raster files or running raster math.

Always evaluate if you need historical context before answering. 
If a user asks a general question that does not require tools, answer it directly.
Be concise and authoritative.
"""

    supervisor_builder = create_supervisor(
        agents=[
            vector_agent,
            raster_agent,
            memory_agent
        ],
        model=model,
        prompt=SUPERVISOR_PROMPT
    )
    
    return supervisor_builder.compile(checkpointer=checkpointer)

# Instantiate the global graph ready with the Redis Checkpointer
app_graph = get_supervisor(checkpointer=memory_saver)
