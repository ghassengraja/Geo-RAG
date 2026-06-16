import asyncpg
from pgvector.asyncpg import register_vector
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabasePool:
    pool: asyncpg.Pool = None

    @classmethod
    async def init_pool(cls):
        logger.info("Initializing PostgreSQL connection pool...")
        cls.pool = await asyncpg.create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT
        )
        
        async with cls.pool.acquire() as conn:
            # Create PostGIS and pgvector extensions
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            
            # Register pgvector codec
            await register_vector(conn)
            
            # Create LTM schema
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    summary TEXT NOT NULL,
                    embedding vector({settings.VECTOR_DIM}),
                    geom GEOMETRY(Geometry, 4326),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create spatial index
                CREATE INDEX IF NOT EXISTS episodic_memory_geom_idx 
                ON episodic_memory USING GIST(geom);
            """)
        logger.info("Database schema and pool initialized.")

    @classmethod
    async def close_pool(cls):
        if cls.pool:
            await cls.pool.close()
            logger.info("PostgreSQL connection pool closed.")

async def get_db_pool() -> asyncpg.Pool:
    return DatabasePool.pool
