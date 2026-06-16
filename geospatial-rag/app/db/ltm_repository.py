import asyncpg
from typing import List, Dict, Any, Optional
from app.db.connection import get_db_pool

async def insert_episode(session_id: str, summary: str, embedding: List[float], geojson_geometry: Optional[str] = None):
    """
    Saves a session episode to the LTM database.
    geojson_geometry is an optional string containing a GeoJSON Geometry object representing the bounding box or point.
    """
    pool = await get_db_pool()
    query = """
        INSERT INTO episodic_memory (session_id, summary, embedding, geom)
        VALUES ($1, $2, $3, ST_GeomFromGeoJSON($4))
    """ if geojson_geometry else """
        INSERT INTO episodic_memory (session_id, summary, embedding)
        VALUES ($1, $2, $3)
    """
    
    async with pool.acquire() as conn:
        if geojson_geometry:
            await conn.execute(query, session_id, summary, embedding, geojson_geometry)
        else:
            await conn.execute(query, session_id, summary, embedding)

async def retrieve_semantic_spatial_context(embedding: List[float], geojson_geometry: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves context using pgvector <-> distance.
    If geojson_geometry is provided, strictly filters by spatial intersection.
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        if geojson_geometry:
            # Hybrid search: semantic similarity filtered by spatial intersection
            query = """
                SELECT session_id, summary, created_at, 
                       ST_AsGeoJSON(geom) as geom_json,
                       embedding <-> $1 AS distance
                FROM episodic_memory
                WHERE ST_Intersects(geom, ST_GeomFromGeoJSON($2))
                ORDER BY distance ASC
                LIMIT $3;
            """
            rows = await conn.fetch(query, embedding, geojson_geometry, limit)
        else:
            # Pure semantic search
            query = """
                SELECT session_id, summary, created_at, 
                       ST_AsGeoJSON(geom) as geom_json,
                       embedding <-> $1 AS distance
                FROM episodic_memory
                ORDER BY distance ASC
                LIMIT $2;
            """
            rows = await conn.fetch(query, embedding, limit)
            
    return [dict(row) for row in rows]
