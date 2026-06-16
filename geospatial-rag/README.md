# Geospatial RAG Application

A Multi-Agent AI system designed to analyze, interact with, and memorize Big Geospatial Data. It integrates a **LangGraph Supervisor** architecture with a robust big data backend (Apache Spark, Hadoop, HBase, GeoMesa, GeoTrellis) and a geospatial database (PostgreSQL/PostGIS + pgvector).

## Architecture

### 1. Multi-Agent System (LangGraph)
The AI is built on a Hub-and-Spoke (Star) topology orchestrated by `langgraph-supervisor`:

- **Supervisor Agent (`app/ai/supervisor.py`):**
  The central orchestrator. It receives user inputs, analyzes the intent, and delegates tasks to specialized sub-agents. It acts as the principal Geospatial Architect.
  
- **Geo Agent (`app/ai/agents.py`):**
  A specialized data engineer agent.
  - Submits heavy jobs to **Apache Spark**.
  - Ingests vector data (GeoJSON) into **GeoMesa / HBase**.
  - Ingests raster data (GeoTIFF) into **GeoTrellis / HBase** via GeoPySpark.
  - Calculates intersections and feature counts at scale.

- **Memory Agent (`app/ai/agents.py`):**
  An autonomous librarian agent for **Geospatial Episodic Memory**.
  - Has tools to *search, add, update, and delete* facts.
  - Maintains a database of deduplicated facts categorized by **Region and Place Name**.
  - Employs a strict deduplication workflow to keep the database clean and relevant.

### 2. State & Memory Management
- **Short-Term Checkpointing:** We use **Redis** (`AsyncRedisSaver`) for fast, distributed storage of the immediate LangGraph message state.
- **Long-Term Episodic Memory:** We use **PostgreSQL with PostGIS and pgvector** (`app/db/connection.py`). The Memory Agent uses Hybrid Search: Semantic distance filtering (via `pgvector`) combined with Spatial intersection (via `PostGIS GIST index`).

### 3. Backend Infrastructure (Docker)
The system runs via `docker-compose`:
- **Hadoop (Namenode & Datanode):** Underlying HDFS storage.
- **Zookeeper & HBase (Master & RegionServer):** Distributed NoSQL storage for GeoMesa catalogs.
- **Apache Spark (Master & Worker):** Distributed compute for spatial operations.
- **PostgreSQL:** Handles the Episodic Memory using PostGIS geometries.
- **Redis:** Serves as the LangGraph state Checkpointer.

## Getting Started
1. Boot up the infrastructure: `docker-compose up -d`
2. Start the FastAPI server: `uv run uvicorn app.main:app --reload`
3. Communicate via the `/chat` streaming endpoint or close the session via `/session/{session_id}/close`.
