from langchain_core.tools import tool
from typing import Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.db.ltm_repository import retrieve_semantic_spatial_context
from app.config import settings

@tool
async def fetch_ltm_context_tool(query: str, geojson_geometry: Optional[str] = None) -> str:
    """
    Queries the Long-Term Episodic Memory (LTM) for historical context, preferences, or past events.
    Args:
        query: The semantic search query to look for in past conversations.
        geojson_geometry: (Optional) A GeoJSON string representing a polygon or bounding box to strictly filter results geographically.
    """
    # 1. Generate embedding for the query
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=settings.GOOGLE_API_KEY
    )
    query_vector = await embeddings.aembed_query(query)
    
    # 2. Query PostGIS / pgvector
    results = await retrieve_semantic_spatial_context(
        embedding=query_vector, 
        geojson_geometry=geojson_geometry, 
        limit=3
    )
    
    if not results:
        return "No relevant historical context found in Episodic Memory."
        
    formatted_results = []
    for idx, r in enumerate(results):
        formatted_results.append(
            f"Episode {idx+1} (Date: {r['created_at']}):\n"
            f"Summary: {r['summary']}\n"
            f"Geometry: {r['geom_json']}"
        )
        
    return "\n\n".join(formatted_results)
