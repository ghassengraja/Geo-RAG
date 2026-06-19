# Multi-Agent Geospatial RAG System

A state-of-the-art intelligent agent system capable of retrieving, ingesting, and analyzing large-scale geospatial data. It combines Large Language Models (LLMs) via Google's Gemini API with LangGraph orchestrations and Big Data geospatial processing via Apache Spark and GeoMesa.

## Architecture & Components

The platform operates using a containerized backend infrastructure while the Agent Orchestrator (FastAPI) runs on the host machine via `uv`.

### 1. Agent Orchestrator (FastAPI + LangGraph)
- **Role:** The brain of the operation. It receives user prompts, interprets them using Google's Generative AI models, and routes tasks to specialized sub-agents (`memory_agent` and `geo_agent`).
- **Memory & State:** Uses `AsyncRedisSaver` for conversational LangGraph checkpointer memory, and PostGIS (`pgvector`) for Long-Term Episodic Memory. PostGIS acts as a fast spatial index and "Catalog Registry", storing semantic facts, bounding boxes, and a `metadata_payload` (JSON pointer) that links directly to massive datasets stored in HBase.
- **Key Sub-Agents & Tools:**
  - `geosupervisor`: A nested supervisor orchestrator that sits beneath the Master Supervisor. It exclusively handles routing complex spatial data payloads down to either the `raster_agent` or `vector_agent`.
  - `search_episodic_memory` / `add_region_memory`: Interacts with PostGIS and pgvector to manage and retrieve Long-Term Episodic Memory (past chats, preferences, previous location context) through vector embeddings.
  - `search_documentation_tool`: A standalone RAG retrieval tool pointing to a local ChromaDB instance containing library documentation (GeoTrellis/GeoMesa).
  - `execute_custom_scala_job_tool`: A highly privileged execution tool that allows agents to synthesize and execute custom Scala code dynamically on the Spark cluster.
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
- **ChromaDB (Local):**
  - Stores specialized documentation embeddings for API introspection, completely separate from the episodic conversational memory stored in PostGIS.
- **Redis (`redis`):**
  - Stores LangGraph conversational checkpoints.

## Workflow Pipeline
1. **User Request:** "Calculate the vegetation index for the Sfax data I uploaded yesterday."
2. **Context Retrieval:** The LangGraph Supervisor triggers the `memory_agent` (Context Engine) to semantically search PostGIS. It instantly retrieves the fact, the bounding box, and the `metadata_payload` pointing to the exact HBase catalog and layer name.
3. **Heavy Workload Execution:** The Supervisor passes these metadata pointers to the `raster_agent` or `vector_agent` (Heavy Machinery). The agent dispatches a GeoTrellis Scala or PySpark job to Apache Livy, running the distributed computation directly over HBase without moving any data.

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
