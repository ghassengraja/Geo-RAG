from langgraph.prebuilt import create_react_agent

from app.ai.llm import get_model
from app.ai.tools.vector_tools import vector_tools
from app.ai.tools.raster_tools import raster_tools
from app.ai.tools.ltm_tools import ltm_tools

def get_vector_agent(checkpointer=None):
    model = get_model()
    vector_prompt = """You are a specialized Geospatial Vector Big Data Agent.
Your job is to run heavy calculation tasks using GeoMesa, ingest vector data (like GeoJSON) into HBase, list available spatial catalogs, and introspect vector data.
You can use `describe_schema_tool` to get the CRS and attributes of a dataset, `get_feature_names_tool` to find layers inside a catalog, `analyze_stats_tool` to get bounding boxes and counts, and `export_spatial_data_tool` to sample data.
Use the appropriate tool for the job. Do not make assumptions about data paths or schemas, use your introspection tools to verify them first.

CRITICAL INSTRUCTION: If the user asks a multi-part question and some parts are outside your domain, ONLY answer the questions you have tools for. Do not apologize or mention that you cannot answer the other questions. Do not ask the user to transfer you. The Supervisor will automatically route the remaining questions to the correct agent.
"""
    agent = create_react_agent(
        model=model,
        tools=vector_tools,
        prompt=vector_prompt,
        checkpointer=checkpointer
    )
    return agent

def get_raster_agent(checkpointer=None):
    model = get_model()
    raster_prompt = """You are a specialized Geospatial Raster Big Data Agent.
Your job is to ingest raster data (like GeoTIFFs) into a distributed GeoTrellis catalog in HBase and perform raster-based operations using Spark.
You can use `get_raster_metadata_tool` to check a raster's CRS and bounds, `retrieve_raster_tile_tool` to crop out a specific bounding box and export it, and `calculate_map_algebra_tool` to run distributed pixel math (like thresholding).
Use the appropriate tool for the job. Do not make assumptions about data paths, use the ones provided.

CRITICAL INSTRUCTION: If the user asks a multi-part question and some parts are outside your domain, ONLY answer the questions you have tools for. Do not apologize or mention that you cannot answer the other questions. Do not ask the user to transfer you. The Supervisor will automatically route the remaining questions to the correct agent.
"""
    agent = create_react_agent(
        model=model,
        tools=raster_tools,
        prompt=raster_prompt,
        checkpointer=checkpointer
    )
    return agent

def get_memory_agent(checkpointer=None):
    model = get_model()
    ltm_prompt = """You are a specialized geospatial memory agent. Your job is to maintain a database of facts about Regions and Places.
When asked to save facts about a location, you MUST follow this strict deduplication workflow:
1. Search if the fact about the place already exists using `search_episodic_memory`.
2. If a fact already exists but is outdated, use `update_episodic_memory` using its ID.
3. If a fact directly contradicts the new truth and shouldn't just be updated, use `delete_episodic_memory`.
4. Only if the fact is completely new, use `add_episodic_memory`.

CRITICAL INSTRUCTION: If the user asks a multi-part question and some parts are outside your domain, ONLY answer the questions you have tools for. Do not apologize or mention that you cannot answer the other questions. Do not ask the user to transfer you. The Supervisor will automatically route the remaining questions to the correct agent.
"""
    agent = create_react_agent(
        model=model,
        tools=ltm_tools,
        prompt=ltm_prompt,
        checkpointer=checkpointer
    )
    return agent
