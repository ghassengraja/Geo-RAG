from langgraph.prebuilt import create_react_agent

from app.ai.llm import get_model
from app.ai.tools.geo_tools import geo_tools
from app.ai.tools.ltm_tools import ltm_tools

def get_geo_agent(checkpointer=None):
    model = get_model()
    geo_prompt = """You are a specialized Geospatial Big Data Agent.
Your job is to run heavy calculation tasks using Spark and GeoMesa or ingest vector/raster data into HBase.
Use the appropriate tool for the job. Do not make assumptions about data paths, use the ones provided.
"""
    agent = create_react_agent(
        model=model,
        tools=geo_tools,
        prompt=geo_prompt,
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
"""
    agent = create_react_agent(
        model=model,
        tools=ltm_tools,
        prompt=ltm_prompt,
        checkpointer=checkpointer
    )
    return agent
