from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from app.api.routes import router as api_router
from app.db.connection import DatabasePool
from app.ai.supervisor import memory_saver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the DB connection pool and schema
    logger.info("Starting up FastAPI Multi-Agent Geospatial RAG System...")
    await DatabasePool.init_pool()
    await memory_saver.setup()
    
    yield
    
    # Shutdown: Close the pool cleanly
    logger.info("Shutting down...")
    await DatabasePool.close_pool()

app = FastAPI(
    title="Geospatial RAG Multi-Agent API",
    description="FastAPI + LangGraph + Spark + PostGIS backend",
    version="1.0.0",
    lifespan=lifespan
)

# Include the main router
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
