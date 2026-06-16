from langchain_core.tools import tool
from typing import Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.db.ltm_repository import retrieve_semantic_spatial_context, add_region_memory, update_region_memory, delete_region_memory
from app.config import settings

def _get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2", 
        google_api_key=settings.GOOGLE_API_KEY
    )

@tool
async def search_episodic_memory(query: str, place_name: Optional[str] = None, geojson_geometry: Optional[str] = None, limit: int = 5) -> str:
    """
    Search the geospatial episodic memory database to recall past facts about a region or place.
    
    Arguments:
    query: The search query to recall relevant facts.
    place_name: (Optional) Filter by the exact name of the region or place.
    geojson_geometry: (Optional) A GeoJSON string representing a polygon or bounding box to strictly filter results geographically.
    limit: The maximum number of results to return (default 5).
    """
    embeddings = _get_embeddings()
    query_vector = await embeddings.aembed_query(query)
    
    results = await retrieve_semantic_spatial_context(
        embedding=query_vector, 
        place_name=place_name,
        geojson_geometry=geojson_geometry, 
        limit=limit
    )
    
    if not results:
        return "No relevant facts found."
        
    formatted_results = []
    for r in results:
        formatted_results.append(
            f"ID: {r['id']} | Place: {r['place_name']} | Date: {r['created_at']}\n"
            f"Fact: {r['fact']}\n"
            f"Context: {r['context']}\n"
            f"Geometry: {r['geom_json']}"
        )
        
    return "\n\n".join(formatted_results)

@tool
async def add_episodic_memory(place_name: str, fact: str, context: str, geojson_geometry: Optional[str] = None) -> str:
    """
    Save a completely new fact or experience about a place to the episodic memory.
    Use this ONLY after searching to confirm the fact does not already exist.
    
    Arguments:
    place_name: The name of the region or place.
    fact: A concise statement of the fact.
    context: Detailed context or explanation surrounding the fact.
    geojson_geometry: (Optional) A GeoJSON string representing the spatial footprint.
    """
    embeddings = _get_embeddings()
    text_to_embed = f"Place: {place_name}. Fact: {fact}. Context: {context}."
    vector = await embeddings.aembed_query(text_to_embed)
    
    try:
        new_id = await add_region_memory(
            place_name=place_name, 
            fact=fact, 
            context=context, 
            embedding=vector, 
            geojson_geometry=geojson_geometry
        )
        return f"Successfully saved NEW memory ID {new_id} for {place_name}."
    except Exception as e:
        return f"Failed to save memory: {str(e)}"

@tool
async def update_episodic_memory(memory_id: int, fact: str, context: str, geojson_geometry: Optional[str] = None) -> str:
    """
    Update an existing memory with new information.
    Use this when a previously saved fact has changed or needs more context.
    
    Arguments:
    memory_id: The ID integer of the memory to update (obtained from search_episodic_memory).
    fact: The updated concise statement of the fact.
    context: The updated detailed context.
    geojson_geometry: (Optional) A GeoJSON string representing the updated spatial footprint.
    """
    # Since we need place_name for good embedding but it's not passed, we embed the fact directly.
    embeddings = _get_embeddings()
    text_to_embed = f"Fact: {fact}. Context: {context}."
    vector = await embeddings.aembed_query(text_to_embed)
    
    try:
        await update_region_memory(
            memory_id=memory_id,
            fact=fact,
            context=context,
            embedding=vector,
            geojson_geometry=geojson_geometry
        )
        return f"Successfully UPDATED memory ID {memory_id}."
    except Exception as e:
        return f"Failed to update memory: {str(e)}"

@tool
async def delete_episodic_memory(memory_id: int) -> str:
    """
    Delete an existing memory.
    Use this when a previously saved fact is no longer true, directly contradicted, or completely irrelevant.
    
    Arguments:
    memory_id: The ID integer of the memory to delete (obtained from search_episodic_memory).
    """
    try:
        await delete_region_memory(memory_id=memory_id)
        return f"Successfully DELETED memory ID {memory_id}."
    except Exception as e:
        return f"Failed to delete memory: {str(e)}"

ltm_tools = [
    search_episodic_memory,
    add_episodic_memory,
    update_episodic_memory,
    delete_episodic_memory
]
