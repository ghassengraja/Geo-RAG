# Multi-Agent Geospatial RAG System

A state-of-the-art intelligent agent system capable of retrieving, ingesting, and analyzing large-scale geospatial data. It combines Large Language Models (LLMs) with LangGraph orchestrations and Big Data geospatial processing via Apache Spark and GeoMesa.

## Architecture & Components

The platform operates using a containerized backend infrastructure while the Agent Orchestrator (FastAPI) runs on the host machine.

### 1. Agent Orchestrator (FastAPI + LangGraph)
- **Role:** The brain of the operation. It receives user prompts, interprets them using Google's Gemini models, and routes tasks to specialized tools.
- **Tools:**
  - `fetch_ltm_context_tool`: Interacts with PostGIS to retrieve Long-Term Memory (past chats, preferences, previous location context).
  - `ingest_geospatial_data_tool`: Dynamically ingests files (like GeoJSON) directly into HBase by communicating with the Docker Daemon (`docker exec`).
  - `geospatial_calculation_tool`: Initiates PySpark sessions to execute heavy `st_intersects` spatial queries over billions of points.

### 2. Big Data Infrastructure (Dockerized)
- **Hadoop & HBase (`hbase-master`, `namenode`, `datanode`):**
  - Serves as the distributed data store for massive geospatial datasets.
  - GeoMesa sits on top of HBase, converting complex geometries (polygons, lines, points) into Space-Filling Curves (Z-order indexing) for lightning-fast spatial queries.
- **Apache Spark (`spark-master`, `spark-worker`):**
  - The distributed computing engine. The FastAPI agent acts as the Spark Driver, dispatching spatial SQL queries (e.g. `SELECT count(*) WHERE st_intersects(...)`) to the Spark workers.
- **PostgreSQL / PostGIS (`postgres`):**
  - Stores the application state, user conversational history, and vectors for the RAG architecture.

## Workflow Pipeline
1. **User Request:** "Ingest this tunisia.geojson file"
2. **LLM Routing:** The LangGraph Supervisor recognizes an ingestion task and triggers the ingestion tool.
3. **Execution:** The FastAPI agent fires a `docker exec` command to the `hbase-master` container to parse and ingest the GeoJSON using the GeoMesa CLI.
4. **Follow-up Request:** "How many features intersect with point X?"
5. **Spark Calculation:** The agent provisions an ephemeral Spark Session, loads the GeoMesa HBase catalog, and runs a distributed `st_intersects` query.

## Prerequisites
- **Python 3.12+** (managed via `uv`)
- **Docker & Docker Compose**
- **GeoMesa Spark Runtime Jar:** Required for PySpark to read from GeoMesa. Mapped to `/home/ghassen/Bureau/data/geomesa_jars/`.

## Running the Application
1. Start the infrastructure:
   ```bash
   docker-compose up -d
   ```
2. Start the Agent API:
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
3. Access the interactive Swagger UI at `http://localhost:8000/docs`.
