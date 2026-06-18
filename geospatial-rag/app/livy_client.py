import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class LivyClient:
    def __init__(self, host="http://172.18.0.6:8998"):
        self.host = host
        self.pyspark_session_id = None
        self.scala_session_id = None
        self.client = httpx.AsyncClient(timeout=60.0)

    async def init_session(self):
        """Initializes PySpark and Scala sessions in Apache Livy."""
        self.pyspark_session_id = await self._create_session("pyspark")
        self.scala_session_id = await self._create_session("spark")

    async def _create_session(self, kind: str) -> int:
        logger.info(f"Initializing Apache Livy {kind} Session...")
        payload = {
            "kind": kind,
            "name": f"FastAPI-GeoRAG-Livy-{kind}",
            "conf": {
                "spark.jars": "local:/datapc/geomesa_jars/geomesa-hbase-spark-runtime-hbase2_2.12-3.5.2.jar"
            }
        }
        
        try:
            response = await self.client.post(f"{self.host}/sessions", json=payload)
            response.raise_for_status()
            session_id = response.json()["id"]
            logger.info(f"Created Livy Session ID: {session_id} ({kind}). Waiting for 'idle' state...")
            
            while True:
                res = await self.client.get(f"{self.host}/sessions/{session_id}")
                state = res.json()["state"]
                if state == "idle":
                    logger.info(f"Livy {kind} Session is ready and warm!")
                    return session_id
                elif state in ["error", "dead", "shutting_down"]:
                    raise Exception(f"Livy {kind} Session failed with state: {state}")
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Failed to initialize Livy {kind} session: {e}")
            raise e

    async def execute_code(self, code: str) -> str:
        """Executes a PySpark code snippet on the Livy server."""
        return await self._execute_statement(self.pyspark_session_id, code)

    async def execute_scala_code(self, code: str) -> str:
        """Executes a Scala code snippet on the Livy server."""
        return await self._execute_statement(self.scala_session_id, code)

    async def _execute_statement(self, session_id: int, code: str) -> str:
        if session_id is None:
            raise Exception("Livy session not initialized.")
            
        logger.info(f"Submitting code to Livy Session {session_id}...")
        payload = {"code": code}
        
        res = await self.client.post(f"{self.host}/sessions/{session_id}/statements", json=payload)
        res.raise_for_status()
        statement_id = res.json()["id"]
        
        while True:
            res = await self.client.get(f"{self.host}/sessions/{session_id}/statements/{statement_id}")
            data = res.json()
            state = data["state"]
            
            if state == "available":
                output = data.get("output", {})
                if output.get("status") == "error":
                    error_msg = output.get("evalue", "Unknown error")
                    raise Exception(f"Livy Error: {error_msg}")
                
                result_data = output.get("data", {})
                return result_data.get("text/plain", "")
                
            elif state in ["error", "cancelled"]:
                raise Exception(f"Statement failed with state: {state}")
                
            await asyncio.sleep(0.5)

    async def close(self):
        for sid in [self.pyspark_session_id, self.scala_session_id]:
            if sid is not None:
                logger.info(f"Shutting down Livy Session {sid}...")
                await self.client.delete(f"{self.host}/sessions/{sid}")
        await self.client.aclose()

livy_client = LivyClient()
