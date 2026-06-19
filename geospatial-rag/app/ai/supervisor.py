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
    
    GEOSUPERVISOR_PROMPT = """You are the GeoSupervisor, an orchestrator for heavy spatial workloads.
Your job is to route tasks between your two specialized agents:
- `vector_agent`: Use this for executing heavy spatial workloads and Big Data operations using GeoMesa/Spark (e.g., Shapefiles, GeoJSON, Points, Polygons, intersections).
- `raster_agent`: Use this for executing heavy raster pixel operations using GeoTrellis/Spark (e.g., GeoTIFFs, map algebra, vegetation indices).
"""

    geosupervisor_builder = create_supervisor(
        agents=[vector_agent, raster_agent],
        model=model,
        prompt=GEOSUPERVISOR_PROMPT
    )
    
    # We compile without a checkpointer for the inner graph, or we can use the same checkpointer.
    # Usually nested supervisors work best when compiled natively.
    geosupervisor = geosupervisor_builder.compile()
    geosupervisor.name = "geosupervisor"
    
    SUPERVISOR_PROMPT = """You are a Principal Enterprise AI Architect and Geospatial Analyst. 
You act as the Master Orchestrator in a Multi-Agent Geospatial RAG system. Your job is to route requests to the correct specialized agents.

AGENT CAPABILITIES & WORKFLOW:
- `memory_agent`: The "Context Engine". Use this agent for lightweight, fast contextual tasks. It searches the PostGIS database for facts, metadata payloads, and bounding boxes. Always use this agent FIRST if a user asks a contextual question (e.g., "What do we know about Sfax?") to retrieve the metadata pointers.
- `geosupervisor`: The "Heavy Machinery Orchestrator". Use this to execute ANY heavy spatial workloads and Big Data operations. It manages the `raster_agent` and `vector_agent` internally. Route any request involving data ingestion, spatial queries, or map algebra to this supervisor. Pass it the metadata payload from the memory agent so it knows exactly what data to run the heavy workload on.

IMPORTANT ROUTING LOGIC:
The agents are designed to work together! If a user asks for a complex analysis on a past dataset, you should:
1. Route to `memory_agent` first to retrieve the semantic context and the exact `metadata_payload` (catalog/layer pointers) from PostGIS.
2. Route to `geosupervisor` and pass it the metadata payload.

If a user asks a general question that does not require tools, answer it directly.
Be concise and authoritative.
"""

    supervisor_builder = create_supervisor(
        agents=[
            memory_agent,
            geosupervisor
        ],
        model=model,
        prompt=SUPERVISOR_PROMPT
    )
    
    return supervisor_builder.compile(checkpointer=checkpointer)

# Instantiate the global graph ready with the Redis Checkpointer
app_graph = get_supervisor(checkpointer=memory_saver)
