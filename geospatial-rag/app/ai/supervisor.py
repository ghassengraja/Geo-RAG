from langgraph_supervisor import create_supervisor
from app.ai.llm import get_model
from app.ai.agents import get_geo_agent, get_memory_agent
from langgraph.checkpoint.redis import AsyncRedisSaver
import redis.asyncio as redis
from app.config import settings

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=False)
redis_client = redis.Redis(connection_pool=redis_pool)
memory_saver = AsyncRedisSaver(redis_client=redis_client)


def get_supervisor(model=None, checkpointer=None):
    if model is None:
        model = get_model()
        
    geo_agent = get_geo_agent(checkpointer=checkpointer)
    memory_agent = get_memory_agent(checkpointer=checkpointer)
    
    geo_agent.name = "geo_agent"
    memory_agent.name = "memory_agent"
    
    SUPERVISOR_PROMPT = """You are a Principal Enterprise AI Architect and Geospatial Analyst. 
You act as the Supervisor Orchestrator in a Multi-Agent Geospatial RAG system.

You can delegate tasks to the following sub-agents:
- `memory_agent`: Use this to remember past user interactions, preferences, or episodic memories stored in the PostGIS database. If the user mentions a location or asks "what did we do last time", delegate to this agent.
- `geo_agent`: Use this to route heavy data calculation tasks (like spatial intersects, counts) or to ingest files (like GeoJSON vectors or GeoTIFF rasters) into the Big Data cluster.

Always evaluate if you need historical context before answering. 
If a user asks a general question that does not require tools, answer it directly.
Be concise and authoritative.
"""

    supervisor_builder = create_supervisor(
        agents=[
            geo_agent,
            memory_agent
        ],
        model=model,
        prompt=SUPERVISOR_PROMPT
    )
    
    return supervisor_builder.compile(checkpointer=checkpointer)

# Instantiate the global graph ready with the Redis Checkpointer
app_graph = get_supervisor(checkpointer=memory_saver)
