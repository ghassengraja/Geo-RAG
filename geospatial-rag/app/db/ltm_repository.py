import asyncpg
from typing import List, Dict, Any, Optional
from app.db.connection import get_db_pool

async def retrieve_semantic_spatial_context(embedding: List[float], place_name: Optional[str] = None, geojson_geometry: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves context using pgvector <-> distance.
    Filters by place_name or spatial intersection if provided.
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        if geojson_geometry and place_name:
            query = """
                SELECT id, place_name, fact, context, metadata_payload::text, created_at, 
                       ST_AsGeoJSON(geom) as geom_json,
                       embedding <#> $1 AS distance
                FROM episodic_memory
                WHERE place_name = $2 AND ST_Intersects(geom, ST_GeomFromGeoJSON($3))
                ORDER BY distance ASC
                LIMIT $4;
            """
            rows = await conn.fetch(query, embedding, place_name, geojson_geometry, limit)
        elif geojson_geometry:
            query = """
                SELECT id, place_name, fact, context, metadata_payload::text, created_at, 
                       ST_AsGeoJSON(geom) as geom_json,
                       embedding <#> $1 AS distance
                FROM episodic_memory
                WHERE ST_Intersects(geom, ST_GeomFromGeoJSON($2))
                ORDER BY distance ASC
                LIMIT $3;
            """
            rows = await conn.fetch(query, embedding, geojson_geometry, limit)
        elif place_name:
            query = """
                SELECT id, place_name, fact, context, metadata_payload::text, created_at, 
                       ST_AsGeoJSON(geom) as geom_json,
                       embedding <#> $1 AS distance
                FROM episodic_memory
                WHERE place_name = $2
                ORDER BY distance ASC
                LIMIT $3;
            """
            rows = await conn.fetch(query, embedding, place_name, limit)
        else:
            query = """
                SELECT id, place_name, fact, context, metadata_payload::text, created_at, 
                       ST_AsGeoJSON(geom) as geom_json,
                       embedding <#> $1 AS distance
                FROM episodic_memory
                ORDER BY distance ASC
                LIMIT $2;
            """
            rows = await conn.fetch(query, embedding, limit)
            
    return [dict(row) for row in rows]

async def add_region_memory(place_name: str, fact: str, context: str, embedding: List[float], geojson_geometry: Optional[str] = None, metadata_payload: Optional[str] = None) -> int:
    """
    Saves a new fact to the LTM database. Returns the generated ID.
    """
    pool = await get_db_pool()
    query = """
        INSERT INTO episodic_memory (place_name, fact, context, embedding, geom, metadata_payload)
        VALUES ($1, $2, $3, $4, ST_GeomFromGeoJSON($5), $6::jsonb)
        RETURNING id
    """ if geojson_geometry else """
        INSERT INTO episodic_memory (place_name, fact, context, embedding, metadata_payload)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id
    """
    
    async with pool.acquire() as conn:
        if geojson_geometry:
            row = await conn.fetchrow(query, place_name, fact, context, embedding, geojson_geometry, metadata_payload)
        else:
            row = await conn.fetchrow(query, place_name, fact, context, embedding, metadata_payload)
        return row['id']

async def update_region_memory(memory_id: int, fact: str, context: str, embedding: List[float], geojson_geometry: Optional[str] = None, metadata_payload: Optional[str] = None):
    """
    Updates an existing memory.
    """
    pool = await get_db_pool()
    query = """
        UPDATE episodic_memory 
        SET fact = $2, context = $3, embedding = $4, geom = ST_GeomFromGeoJSON($5), metadata_payload = $6::jsonb
        WHERE id = $1
    """ if geojson_geometry else """
        UPDATE episodic_memory 
        SET fact = $2, context = $3, embedding = $4, metadata_payload = $5::jsonb
        WHERE id = $1
    """
    async with pool.acquire() as conn:
        if geojson_geometry:
            await conn.execute(query, memory_id, fact, context, embedding, geojson_geometry, metadata_payload)
        else:
            await conn.execute(query, memory_id, fact, context, embedding, metadata_payload)

async def delete_region_memory(memory_id: int):
    """
    Deletes a memory by ID.
    """
    pool = await get_db_pool()
    query = "DELETE FROM episodic_memory WHERE id = $1"
    async with pool.acquire() as conn:
        await conn.execute(query, memory_id)
