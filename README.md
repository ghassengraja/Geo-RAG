# Multi-Agent Geospatial RAG System

A state-of-the-art intelligent agent system capable of retrieving, ingesting, and analyzing large-scale geospatial data. It combines Large Language Models (LLMs) via Google's Gemini API with LangGraph orchestrations and Big Data geospatial processing via Apache Spark and GeoMesa.

## Architecture & Components

The platform operates using a containerized backend infrastructure while the Agent Orchestrator (FastAPI) runs on the host machine via `uv`.

### 1. Agent Orchestrator (FastAPI + LangGraph)
- **Role:** The brain of the operation. It receives user prompts, interprets them using Google's Generative AI models, and routes tasks to specialized sub-agents (`memory_agent` and `geo_agent`).
- **Memory & State:** Uses `AsyncRedisSaver` (with Redis and RediSearch indices) for conversational LangGraph checkpointer memory, and PostGIS (`pgvector`) for storing episodic memory and semantic spatial context.
- **Key Sub-Agent Tools:**
  - `search_episodic_memory` / `add_region_memory`: Interacts with PostGIS and pgvector to manage and retrieve Long-Term Episodic Memory (past chats, preferences, previous location context) through vector embeddings.
  - `ingest_geospatial_data_tool`: Natively ingests files (like GeoJSON) directly into HBase by initializing PySpark sessions and utilizing the GeoMesa Spark Converter API (bypassing Docker CLI).
  - `geospatial_calculation_tool`: Initiates ephemeral PySpark sessions to execute heavy distributed `st_intersects` spatial queries over massive datasets stored in HBase.
  - `ingest_raster_data_tool`: Natively ingests GeoTIFF files into HBase using PySpark and GeoTrellis.
  - `get_raster_metadata_tool`: Retrieves CRS, Extent, and CellType metadata for raster layers directly from the GeoTrellis catalog.
  - `list_spatial_files_tool`: Uses PySpark's JVM Gateway (Py4J) to communicate directly with HBase and list all currently available spatial catalogs and tables.

### 2. Big Data Infrastructure (Dockerized)
- **Hadoop & HBase (`hbase-master`, `namenode`, `datanode`):**
  - Serves as the distributed data store for massive geospatial datasets.
  - GeoMesa sits on top of HBase, converting complex geometries (polygons, lines, points) into Space-Filling Curves (Z-order indexing) for lightning-fast spatial queries.
- **Apache Spark (`spark-master`, `spark-worker`):**
  - The distributed computing engine. The FastAPI agent acts as the Spark Driver, connecting to the Spark workers over the network to dispatch spatial SQL queries or data ingestion tasks.
- **PostgreSQL / PostGIS (`postgres`):**
  - Stores the conversational history, episodic facts, and generates embeddings for the RAG architecture using `pgvector`.
- **Redis (`redis`):**
  - Stores LangGraph conversational checkpoints.

## Workflow Pipeline
1. **User Request:** "List available spatial files and ingest this tunisia.geojson file."
2. **LLM Routing:** The LangGraph Supervisor interprets the request and triggers the `geo_agent`.
3. **Listing Execution:** The `geo_agent` calls `list_spatial_files_tool`, which spins up PySpark and uses Java Admin APIs to query the HBase Zookeeper for existing tables.
4. **Ingestion Execution:** The `geo_agent` calls `ingest_geospatial_data_tool`, which spins up PySpark, reads the GeoJSON using the GeoMesa converter format, and writes the DataFrame directly to HBase.
5. **Follow-up Request:** "How many features intersect with point X?"
6. **Spark Calculation:** The agent provisions an ephemeral Spark Session, loads the GeoMesa HBase catalog into a DataFrame, and runs a distributed `st_intersects` query.

## Prerequisites
- **Python 3.12+** (managed via `uv`)
- **Docker & Docker Compose**
- **GeoMesa Spark Runtime Jar:** Required for PySpark to read from/write to GeoMesa natively. Mapped to `/home/ghassen/Bureau/data/geomesa_jars/`.
- **GeoTrellis Offline Jars:** Pre-downloaded GeoTrellis, Monocle, and HBase dependencies injected into `/spark/jars/` for offline reliability.

## Running the Application
1. Start the infrastructure:
   ```bash
   docker-compose up -d
   ```
2. Start the Agent API:
   ```bash
   uv run python -m app.main
   ```
3. Access the interactive Swagger UI at `http://localhost:8000/docs`.
