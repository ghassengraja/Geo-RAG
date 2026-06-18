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
        
        # 1. Create extensions using a single temporary connection before setting up the pool
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT
        )
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        await conn.close()

        # 2. Register the pgvector codec on every new connection in the pool
        async def init_connection(conn):
            await register_vector(conn)

        # 3. Create the pool
        cls.pool = await asyncpg.create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            init=init_connection
        )
        
        # 4. Create LTM schema
        async with cls.pool.acquire() as db_conn:
            await db_conn.execute(f"""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id SERIAL PRIMARY KEY,
                    place_name VARCHAR(255) NOT NULL,
                    fact TEXT NOT NULL,
                    context TEXT,
                    embedding vector({settings.VECTOR_DIM}),
                    geom GEOMETRY(Geometry, 4326),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create spatial index (GiST)
                CREATE INDEX IF NOT EXISTS episodic_memory_geom_idx 
                ON episodic_memory USING GIST(geom);
                
                -- Create B-Tree index for faster place name lookups
                CREATE INDEX IF NOT EXISTS episodic_memory_place_name_idx 
                ON episodic_memory (place_name);
                
                -- Create HNSW index for fast approximate nearest neighbor vector search
                CREATE INDEX IF NOT EXISTS episodic_memory_embedding_idx 
                ON episodic_memory USING hnsw (embedding vector_l2_ops);
            """)
        logger.info("Database schema and pool initialized.")

    @classmethod
    async def close_pool(cls):
        if cls.pool:
            await cls.pool.close()
            logger.info("PostgreSQL connection pool closed.")

async def get_db_pool() -> asyncpg.Pool:
    return DatabasePool.pool
