# Multi-Agent Geospatial RAG System

A state-of-the-art intelligent agent system capable of retrieving, ingesting, and analyzing large-scale geospatial data. It combines Large Language Models (LLMs) via Google's Gemini API with LangGraph orchestrations and Big Data geospatial processing via Apache Spark and GeoMesa.

## Architecture & Components

The platform operates using a containerized backend infrastructure while the Agent Orchestrator (FastAPI) runs on the host machine via `uv`.

### 1. Agent Orchestrator (FastAPI + LangGraph)
- **Role:** The brain of the operation. It receives user prompts, interprets them using Google's Generative AI models, and routes tasks to specialized sub-agents (`memory_agent` and `geo_agent`).
- **Memory & State:** Uses `AsyncRedisSaver` (with Redis and RediSearch indices) for conversational LangGraph checkpointer memory, and PostGIS (`pgvector`) for storing episodic memory and semantic spatial context.
- **Key Sub-Agent Tools:**
  - `search_episodic_memory` / `add_region_memory`: Interacts with PostGIS and pgvector to manage and retrieve Long-Term Episodic Memory (past chats, preferences, previous location context) through vector embeddings.
  - `ingest_geospatial_data_tool`: Ingests files (like GeoJSON) directly into HBase by orchestrating the GeoMesa CLI tools inside the Hadoop cluster.
  - `geospatial_calculation_tool`: Executes heavy distributed `st_intersects` spatial queries over massive datasets stored in HBase via the Apache Livy REST API (PySpark).
  - `ingest_raster_data_tool`: Natively ingests GeoTIFF files into HBase using GeoTrellis, submitted as Scala jobs to Spark via Apache Livy.
  - `get_raster_metadata_tool`: Retrieves CRS, Extent, and CellType metadata for raster layers directly from the GeoTrellis catalog via Apache Livy.
  - `list_spatial_files_tool`: Uses GeoMesa CLI to list all currently available spatial catalogs and tables.

### 2. Big Data Infrastructure (Dockerized)
- **Hadoop & HBase (`hbase-master`, `namenode`, `datanode`):**
  - Serves as the distributed data store for massive geospatial datasets.
  - GeoMesa sits on top of HBase, converting complex geometries (polygons, lines, points) into Space-Filling Curves (Z-order indexing) for lightning-fast spatial queries.
- **Apache Spark & Livy (`spark-master`, `spark-worker`):**
  - The distributed computing engine. The FastAPI agent acts as a REST client to Apache Livy 0.8.0 (running in the `spark-master`), dispatching spatial SQL and GeoTrellis Scala scripts. This entirely decoupled design prevents Python 3.12/PySpark version mismatches and eliminates JVM startup overhead.
- **PostgreSQL / PostGIS (`postgres`):**
  - Stores the conversational history, episodic facts, and generates embeddings for the RAG architecture using `pgvector`.
- **Redis (`redis`):**
  - Stores LangGraph conversational checkpoints.

## Workflow Pipeline
1. **User Request:** "List available spatial files and ingest this tunisia.geojson file."
2. **LLM Routing:** The LangGraph Supervisor interprets the request and triggers the `geo_agent`.
3. **Listing Execution:** The `geo_agent` calls `list_spatial_files_tool`, which uses the GeoMesa CLI to query the HBase Zookeeper for existing tables.
4. **Ingestion Execution:** The `geo_agent` calls `ingest_geospatial_data_tool`, which triggers the GeoMesa ingestion pipeline.
5. **Follow-up Request:** "How many features intersect with point X?"
6. **Spark Calculation:** The agent submits a PySpark script to the persistent Apache Livy session, loading the GeoMesa HBase catalog into a DataFrame and running a distributed `st_intersects` query in sub-seconds.

## Prerequisites
- **Python 3.12+** (managed via `uv`)
- **Docker & Docker Compose**
- **GeoMesa Spark Runtime Jar:** Required for PySpark to read from/write to GeoMesa natively. Mapped to `/home/ghassen/Bureau/data/geomesa_jars/` and whitelisted in Livy.
- **GeoTrellis Offline Jars:** Pre-downloaded GeoTrellis, Monocle, and HBase dependencies injected into `/spark/jars/` for offline reliability.
- **Apache Livy 0.8.0:** Installed in the `spark-master` container (compiled for Scala 2.12) to serve REST sessions.

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
